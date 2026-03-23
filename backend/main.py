import os
import json
import time
import duckdb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/stock_latest.db")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "models/artifacts")

from models.inference.predict import predict, predict_all
from data_pipeline.fetch_and_store import TICKERS
from ticker_names import TICKER_NAMES

# Deduplicate ticker list (fetch_and_store has some duplicates)
SYMBOLS = list(dict.fromkeys(TICKERS))

VALID_HORIZONS = [1, 5, 14, 30]

app = FastAPI(title="StockPredictor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Prediction cache ─────────────────────────────────────────────────────────

_prediction_cache: dict = {}
_CACHE_TTL = 60  # seconds


def _get_cached_predictions(horizon: int) -> list:
    """Return cached predictions or recompute if stale."""
    now = time.time()
    key = f"h{horizon}"
    if key in _prediction_cache and now - _prediction_cache[key]["ts"] < _CACHE_TTL:
        return _prediction_cache[key]["data"]

    results = predict_all(SYMBOLS, horizon)
    _prediction_cache[key] = {"data": results, "ts": now}
    return results


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """DB status, model freshness, last feature update."""
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        total_symbols = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM eod_prices_clean"
        ).fetchone()[0]
        latest_feature_date = conn.execute(
            "SELECT MAX(date) FROM model_features"
        ).fetchone()[0]
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
        total_symbols = 0
        latest_feature_date = None

    models_saved = len([
        f for f in os.listdir(f"{ARTIFACTS_DIR}/classifiers")
        if f.endswith(".pkl")
    ]) if os.path.isdir(f"{ARTIFACTS_DIR}/classifiers") else 0

    # Read last trained_at from GLOBAL metadata (try new naming first)
    last_trained_at = None
    for meta_name in ["GLOBAL_5d.json", "GLOBAL.json"]:
        global_meta = f"{ARTIFACTS_DIR}/metadata/{meta_name}"
        if os.path.exists(global_meta):
            with open(global_meta) as f:
                last_trained_at = json.load(f).get("trained_at")
            break

    return {
        "db_connected": db_ok,
        "total_symbols_in_db": total_symbols,
        "models_saved": models_saved,
        "last_trained_at": last_trained_at,
        "latest_feature_date": str(latest_feature_date) if latest_feature_date else None,
    }


# ── Predictions ───────────────────────────────────────────────────────────────

@app.get("/api/predictions")
def get_all_predictions(
    sort_by: str = Query("confidence", enum=["confidence", "symbol", "change_1d_pct"]),
    horizon: int = Query(5, enum=[1, 5, 14, 30]),
):
    """
    Predictions for all tracked tickers.
    sort_by: 'confidence' (default), 'symbol', or 'change_1d_pct'
    horizon: prediction horizon in days (1, 5, 14, or 30)
    """
    results = _get_cached_predictions(horizon)

    # Separate errors from valid predictions
    valid = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]

    if sort_by == "confidence":
        valid.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    elif sort_by == "symbol":
        valid.sort(key=lambda x: x["symbol"])
    elif sort_by == "change_1d_pct":
        valid.sort(key=lambda x: x.get("change_1d_pct") or 0, reverse=True)

    return {
        "count": len(valid),
        "horizon": horizon,
        "predictions": valid,
        "errors": errors,
    }


@app.get("/api/predictions/{symbol}")
def get_prediction(
    symbol: str,
    horizon: int = Query(5, enum=[1, 5, 14, 30]),
):
    """Single-stock prediction with SHAP drivers."""
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        raise HTTPException(status_code=404, detail=f"{symbol} is not a tracked ticker.")

    result = predict(symbol, horizon)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# ── Historical prices ─────────────────────────────────────────────────────────

@app.get("/api/historical/{symbol}")
def get_historical(
    symbol: str,
    days: int = Query(default=90, ge=7, le=365),
):
    """
    OHLCV price history for a symbol.
    days: number of calendar days back (7–365, default 90)
    """
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        raise HTTPException(status_code=404, detail=f"{symbol} is not a tracked ticker.")

    conn = duckdb.connect(DB_PATH, read_only=True)
    rows = conn.execute(
        """
        SELECT date, open, high, low, close, volume
        FROM eod_prices_clean
        WHERE symbol = ?
          AND date >= (CURRENT_DATE - INTERVAL (?) DAY)
        ORDER BY date ASC
        """,
        [symbol, days],
    ).fetchdf()
    conn.close()

    if rows.empty:
        raise HTTPException(status_code=404, detail=f"No price data found for {symbol}.")

    return {
        "symbol": symbol,
        "days": days,
        "count": len(rows),
        "prices": rows.to_dict(orient="records"),
    }


# ── Features ──────────────────────────────────────────────────────────────────

@app.get("/api/features/{symbol}")
def get_features(symbol: str):
    """Latest computed feature values for a symbol (useful for debugging)."""
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        raise HTTPException(status_code=404, detail=f"{symbol} is not a tracked ticker.")

    conn = duckdb.connect(DB_PATH, read_only=True)
    row = conn.execute(
        """
        SELECT *
        FROM model_features
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        [symbol],
    ).fetchdf()
    conn.close()

    if row.empty:
        raise HTTPException(status_code=404, detail=f"No features found for {symbol}. Run update_features.py first.")

    return {
        "symbol": symbol,
        "as_of_date": str(row["date"].iloc[0]),
        "features": row.drop(columns=["symbol", "date"]).iloc[0].to_dict(),
    }


# ── Symbols list ──────────────────────────────────────────────────────────────

@app.get("/api/symbols")
def get_symbols():
    """All tracked ticker symbols with company names."""
    return {
        "symbols": sorted(SYMBOLS),
        "names": {s: TICKER_NAMES.get(s, s) for s in SYMBOLS},
        "count": len(SYMBOLS),
    }


# ── Cache invalidation ───────────────────────────────────────────────────────

@app.post("/api/cache/clear")
def clear_cache():
    """Force-clear prediction cache (useful after retraining)."""
    _prediction_cache.clear()
    return {"status": "cleared"}


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "StockPredictor API is running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
