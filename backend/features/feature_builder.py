import duckdb
import numpy as np
import pandas as pd
import os


def _compute_features_for_symbol(g: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical features for a single symbol's price history."""
    g = g.sort_values("date").reset_index(drop=True)

    # ── Log Returns ────────────────────────────────────────────────────────────
    g["log_ret_1d"]  = np.log(g["close"] / g["close"].shift(1))
    g["log_ret_5d"]  = np.log(g["close"] / g["close"].shift(5))
    g["log_ret_14d"] = np.log(g["close"] / g["close"].shift(14))
    g["log_ret_30d"] = np.log(g["close"] / g["close"].shift(30))

    # ── SMA & Price Ratios ─────────────────────────────────────────────────────
    g["sma_20"] = g["close"].rolling(20).mean()
    g["sma_50"] = g["close"].rolling(50).mean()
    g["price_vs_sma20"] = g["close"] / g["sma_20"]
    g["price_vs_sma50"] = g["close"] / g["sma_50"]

    # ── Volatility ─────────────────────────────────────────────────────────────
    g["volatility_20"] = g["log_ret_1d"].rolling(20).std()
    g["volatility_50"] = g["log_ret_1d"].rolling(50).std()

    # ── Volume ─────────────────────────────────────────────────────────────────
    g["avg_vol_20"]   = g["volume"].rolling(20).mean()
    g["volume_ratio"] = g["volume"] / g["avg_vol_20"]

    # ── EMA & EMA Diff (MACD-like signal) ─────────────────────────────────────
    # Normalized so it's comparable across stocks of any price
    ema_12 = g["close"].ewm(span=12, adjust=False).mean()
    ema_26 = g["close"].ewm(span=26, adjust=False).mean()
    g["ema_diff"] = (ema_12 - ema_26) / g["close"]

    # ── RSI (14-period) ────────────────────────────────────────────────────────
    delta = g["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    g["rsi_14"] = 100 - (100 / (1 + rs))

    # ── OBV Signal ─────────────────────────────────────────────────────────────
    # Measures how far OBV has deviated from its 20-day average,
    # normalized by avg daily volume → scale-independent across stocks
    obv = (np.sign(g["close"].diff()) * g["volume"]).cumsum()
    g["obv_signal"] = (obv - obv.rolling(20).mean()) / g["avg_vol_20"].replace(0, np.nan)

    return g


def build_model_features(db_path: str):
    """
    Rebuilds the model_features table from eod_prices_clean.
    Features: log returns, SMA, volatility, volume, EMA, RSI, OBV.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = duckdb.connect(database=db_path, read_only=False)
    print("Loading raw price data...")

    df = conn.execute("""
        SELECT symbol, date, close, volume
        FROM eod_prices_clean
        ORDER BY symbol, date
    """).fetchdf()

    print(f"Computing features for {df['symbol'].nunique()} symbols...")

    groups = [_compute_features_for_symbol(g) for _, g in df.groupby("symbol")]
    features_df = pd.concat(groups, ignore_index=True)

    output_cols = [
        "symbol", "date",
        "log_ret_1d", "log_ret_5d", "log_ret_14d", "log_ret_30d",
        "sma_20", "sma_50", "price_vs_sma20", "price_vs_sma50",
        "volatility_20", "volatility_50",
        "avg_vol_20", "volume_ratio",
        "ema_diff",
        "rsi_14",
        "obv_signal",
    ]
    features_df = features_df[output_cols]

    conn.execute("DROP TABLE IF EXISTS model_features")
    conn.register("features_df", features_df)
    conn.execute("CREATE TABLE model_features AS SELECT * FROM features_df")
    conn.close()

    print("model_features table rebuilt successfully.")
