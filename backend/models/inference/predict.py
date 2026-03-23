import os
import json
import joblib
import duckdb
import pandas as pd

from ticker_names import TICKER_NAMES

DB_PATH       = os.path.join(os.path.dirname(__file__), "../../../data/stock_latest.db")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "../artifacts")

FEATURE_COLS = [
    "log_ret_1d", "log_ret_5d", "log_ret_14d", "log_ret_30d",
    "price_vs_sma20", "price_vs_sma50",
    "volatility_20", "volatility_50",
    "volume_ratio",
    "ema_diff",
    "rsi_14",
    "obv_signal",
]

BUY_THRESHOLD  = 0.60
SELL_THRESHOLD = 0.40


# ── Model loading ─────────────────────────────────────────────────────────────

def _find_meta(symbol: str, horizon: int, suffix: str = "") -> tuple[dict, str] | None:
    """Try new naming ({symbol}_{horizon}d{suffix}.json), then old naming for 5d backward compat."""
    # New naming convention
    meta_path = f"{ARTIFACTS_DIR}/metadata/{symbol}_{horizon}d{suffix}.json"
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return json.load(f), meta_path

    # Backward compat: old naming (only for 5d)
    if horizon == 5:
        old_suffix = "_regressor" if suffix == "_regressor" else ""
        old_path = f"{ARTIFACTS_DIR}/metadata/{symbol}{old_suffix}.json"
        if os.path.exists(old_path):
            with open(old_path) as f:
                return json.load(f), old_path

    return None


def load_model(symbol: str, horizon: int = 5):
    """Load per-ticker classifier, fall back to global. Returns (model, metadata)."""
    # Per-ticker
    result = _find_meta(symbol, horizon)
    if result:
        meta, _ = result
        # Try new naming first
        model_path = f"{ARTIFACTS_DIR}/classifiers/{symbol}_{horizon}d_{meta['model_type']}.pkl"
        if not os.path.exists(model_path) and horizon == 5:
            # Old naming fallback
            model_path = f"{ARTIFACTS_DIR}/classifiers/{symbol}_{meta['model_type']}.pkl"
        if os.path.exists(model_path):
            return joblib.load(model_path), meta

    # Global fallback
    result = _find_meta("GLOBAL", horizon)
    if not result:
        raise FileNotFoundError(
            f"No trained models found for {horizon}d horizon. "
            f"Run: python main_training_pipeline.py --horizon {horizon}"
        )
    meta, _ = result
    model_path = f"{ARTIFACTS_DIR}/classifiers/GLOBAL_{horizon}d_{meta['model_type']}.pkl"
    if not os.path.exists(model_path) and horizon == 5:
        model_path = f"{ARTIFACTS_DIR}/classifiers/GLOBAL_{meta['model_type']}.pkl"
    return joblib.load(model_path), {**meta, "scope": "global_fallback"}


def load_regressor(symbol: str, horizon: int = 5):
    """Load per-ticker regressor, fall back to global. Returns (model, metadata)."""
    # Per-ticker
    result = _find_meta(symbol, horizon, "_regressor")
    if result:
        meta, _ = result
        model_path = f"{ARTIFACTS_DIR}/regressors/{symbol}_{horizon}d_{meta['model_type']}.pkl"
        if not os.path.exists(model_path) and horizon == 5:
            model_path = f"{ARTIFACTS_DIR}/regressors/{symbol}_{meta['model_type']}.pkl"
        if os.path.exists(model_path):
            return joblib.load(model_path), meta

    # Global fallback
    result = _find_meta("GLOBAL", horizon, "_regressor")
    if not result:
        return None, None
    meta, _ = result
    model_path = f"{ARTIFACTS_DIR}/regressors/GLOBAL_{horizon}d_{meta['model_type']}.pkl"
    if not os.path.exists(model_path) and horizon == 5:
        model_path = f"{ARTIFACTS_DIR}/regressors/GLOBAL_{meta['model_type']}.pkl"
    if not os.path.exists(model_path):
        return None, None
    return joblib.load(model_path), {**meta, "scope": "global_fallback"}


# ── DB queries ────────────────────────────────────────────────────────────────

def get_latest_features(symbol: str) -> pd.DataFrame:
    conn = duckdb.connect(DB_PATH, read_only=True)
    row = conn.execute(
        """
        SELECT date, log_ret_1d, log_ret_5d, log_ret_14d, log_ret_30d,
               price_vs_sma20, price_vs_sma50,
               volatility_20, volatility_50,
               volume_ratio, ema_diff, rsi_14, obv_signal
        FROM model_features
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        [symbol],
    ).fetchdf()
    conn.close()
    return row


def get_current_price(symbol: str) -> dict:
    conn = duckdb.connect(DB_PATH, read_only=True)
    rows = conn.execute(
        """
        SELECT date, close
        FROM eod_prices_clean
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT 2
        """,
        [symbol],
    ).fetchdf()
    conn.close()

    if rows.empty:
        return {"current_price": None, "change_1d_pct": None}

    current_price = float(rows.iloc[0]["close"])
    change_1d_pct = None
    if len(rows) == 2:
        prev = float(rows.iloc[1]["close"])
        change_1d_pct = round((current_price - prev) / prev * 100, 2)

    return {"current_price": round(current_price, 2), "change_1d_pct": change_1d_pct}


# ── Prediction ────────────────────────────────────────────────────────────────

def predict(symbol: str, horizon: int = 5) -> dict:
    symbol = symbol.upper()

    features_df = get_latest_features(symbol)
    if features_df.empty:
        return {"symbol": symbol, "error": "No feature data found. Run update_features.py first."}

    X = features_df[FEATURE_COLS]

    # Classifier → direction signal
    try:
        model, meta = load_model(symbol, horizon)
    except FileNotFoundError as e:
        return {"symbol": symbol, "error": str(e)}

    prob_up = float(model.predict_proba(X)[0][1])

    if prob_up >= BUY_THRESHOLD:
        signal = "BUY"
    elif prob_up <= SELL_THRESHOLD:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Regressor → predicted return magnitude
    predicted_return = None
    reg_metrics = {}
    reg, reg_meta = load_regressor(symbol, horizon)
    if reg is not None:
        predicted_return = round(float(reg.predict(X)[0]) * 100, 4)  # as %
        reg_metrics = {
            "rmse": reg_meta.get("rmse"),
            "mae":  reg_meta.get("mae"),
            "r2":   reg_meta.get("r2"),
        }

    # SHAP drivers (only for 5d)
    shap_path = f"{ARTIFACTS_DIR}/shap/{symbol}.json"
    top_drivers = []
    if os.path.exists(shap_path):
        with open(shap_path) as f:
            top_drivers = json.load(f).get("top_drivers", [])

    price_info = get_current_price(symbol)

    return {
        "symbol": symbol,
        "name": TICKER_NAMES.get(symbol, symbol),
        "signal": signal,
        "confidence": round(prob_up, 4),
        "predicted_return_pct": predicted_return,
        "horizon_days": horizon,
        "current_price": price_info["current_price"],
        "change_1d_pct": price_info["change_1d_pct"],
        "top_drivers": top_drivers,
        "model_type": meta.get("model_type"),
        "model_scope": meta.get("scope"),
        "classifier_metrics": {
            "roc_auc":  meta.get("roc_auc"),
            "accuracy": meta.get("accuracy"),
        },
        "regressor_metrics": reg_metrics,
        "trained_at": meta.get("trained_at"),
        "as_of_date": str(features_df["date"].iloc[0])[:10],
    }


def predict_all(symbols: list, horizon: int = 5) -> list:
    results = []
    for symbol in symbols:
        try:
            results.append(predict(symbol, horizon))
        except Exception as e:
            results.append({"symbol": symbol.upper(), "name": TICKER_NAMES.get(symbol.upper(), symbol.upper()), "error": str(e)})
    return results
