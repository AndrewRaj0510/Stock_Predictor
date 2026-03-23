import os
import sys
import json
import warnings
import joblib
import duckdb
import pandas as pd
import numpy as np
from datetime import date

warnings.filterwarnings("ignore", message=".*sklearn.utils.parallel.delayed.*")

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, roc_auc_score,
    mean_squared_error, mean_absolute_error, r2_score,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import xgboost as xgb

from models.explainability.shap_explainer import compute_and_save_shap


DB_PATH       = os.path.join(os.path.dirname(__file__), "../data/stock_latest.db")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "models/artifacts")
MIN_ROWS      = 100

HORIZONS = [1, 5, 14, 30]

FEATURE_COLS = [
    "log_ret_1d", "log_ret_5d", "log_ret_14d", "log_ret_30d",
    "price_vs_sma20", "price_vs_sma50",
    "volatility_20", "volatility_50",
    "volume_ratio",
    "ema_diff",
    "rsi_14",
    "obv_signal",
]


# ── Data loading ──────────────────────────────────────────────────────────────

def load_training_data() -> pd.DataFrame:
    conn = duckdb.connect(DB_PATH, read_only=True)
    query = """
    SELECT
        f.symbol, f.date,
        f.log_ret_1d, f.log_ret_5d, f.log_ret_14d, f.log_ret_30d,
        f.price_vs_sma20, f.price_vs_sma50,
        f.volatility_20, f.volatility_50,
        f.volume_ratio,
        f.ema_diff, f.rsi_14, f.obv_signal,
        t.target_1d, t.target_5d, t.target_14d, t.target_30d,
        t.future_return_1d, t.future_return_5d, t.future_return_14d, t.future_return_30d
    FROM model_features f
    JOIN model_targets t ON f.symbol = t.symbol AND f.date = t.date
    ORDER BY f.symbol, f.date
    """
    df = conn.execute(query).fetchdf()
    conn.close()
    return df.dropna(subset=FEATURE_COLS)


# ── Classifiers ───────────────────────────────────────────────────────────────

def get_classifiers() -> dict:
    return {
        "logistic": LogisticRegression(max_iter=1000, random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
        "xgboost": xgb.XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", random_state=42, n_jobs=-1,
        ),
    }


def evaluate_classifier(clf, X: pd.DataFrame, y: pd.Series, n_splits: int) -> dict:
    tscv = TimeSeriesSplit(n_splits=n_splits)
    aucs, accs = [], []
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        if len(y_test.unique()) < 2:
            continue
        clf.fit(X_train, y_train)
        aucs.append(roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1]))
        accs.append(accuracy_score(y_test, clf.predict(X_test)))
    if not aucs:
        return {"roc_auc": 0.0, "accuracy": 0.0}
    return {"roc_auc": round(float(np.mean(aucs)), 4), "accuracy": round(float(np.mean(accs)), 4)}


def train_best_classifier(X: pd.DataFrame, y: pd.Series, n_splits: int) -> tuple:
    """Evaluate all classifiers, refit best on full data. Returns (name, model, metrics)."""
    best_auc, best_name = -1.0, None
    all_metrics = {}
    for name, clf in get_classifiers().items():
        m = evaluate_classifier(clf, X, y, n_splits)
        all_metrics[name] = m
        if m["roc_auc"] > best_auc:
            best_auc, best_name = m["roc_auc"], name
    winner = get_classifiers()[best_name]
    winner.fit(X, y)
    return best_name, winner, all_metrics[best_name]


# ── Regressors ────────────────────────────────────────────────────────────────

def get_regressors() -> dict:
    return {
        "ridge": Ridge(alpha=1.0),
        "random_forest_reg": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
    }


def evaluate_regressor(reg, X: pd.DataFrame, y: pd.Series, n_splits: int) -> dict:
    tscv = TimeSeriesSplit(n_splits=n_splits)
    rmses, maes, r2s = [], [], []
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        reg.fit(X_train, y_train)
        preds = reg.predict(X_test)
        rmses.append(np.sqrt(mean_squared_error(y_test, preds)))
        maes.append(mean_absolute_error(y_test, preds))
        r2s.append(r2_score(y_test, preds))
    return {
        "rmse": round(float(np.mean(rmses)), 6),
        "mae":  round(float(np.mean(maes)), 6),
        "r2":   round(float(np.mean(r2s)), 4),
    }


def train_best_regressor(X: pd.DataFrame, y: pd.Series, n_splits: int) -> tuple:
    """Evaluate all regressors, refit best (lowest RMSE) on full data. Returns (name, model, metrics)."""
    best_rmse, best_name = float("inf"), None
    all_metrics = {}
    for name, reg in get_regressors().items():
        m = evaluate_regressor(reg, X, y, n_splits)
        all_metrics[name] = m
        if m["rmse"] < best_rmse:
            best_rmse, best_name = m["rmse"], name
    winner = get_regressors()[best_name]
    winner.fit(X, y)
    return best_name, winner, all_metrics[best_name]


# ── Artifact saving ───────────────────────────────────────────────────────────

def save_classifier(model, symbol: str, model_name: str, metrics: dict,
                    scope: str, n_samples: int, X_sample: pd.DataFrame, horizon: int = 5):
    os.makedirs(f"{ARTIFACTS_DIR}/classifiers", exist_ok=True)
    os.makedirs(f"{ARTIFACTS_DIR}/metadata", exist_ok=True)

    joblib.dump(model, f"{ARTIFACTS_DIR}/classifiers/{symbol}_{horizon}d_{model_name}.pkl")

    meta = {
        "symbol": symbol, "model_type": model_name, "scope": scope,
        "roc_auc": metrics["roc_auc"], "accuracy": metrics["accuracy"],
        "n_samples": n_samples, "feature_names": FEATURE_COLS,
        "trained_at": str(date.today()), "horizon_days": horizon,
    }
    with open(f"{ARTIFACTS_DIR}/metadata/{symbol}_{horizon}d.json", "w") as f:
        json.dump(meta, f, indent=2)

    # SHAP only for the primary 5d horizon to keep training time reasonable
    if horizon == 5:
        shap_sample = X_sample.sample(min(300, len(X_sample)), random_state=42)
        compute_and_save_shap(symbol, model, shap_sample, model_name)


def save_regressor(model, symbol: str, model_name: str, metrics: dict,
                   scope: str, n_samples: int, horizon: int = 5):
    os.makedirs(f"{ARTIFACTS_DIR}/regressors", exist_ok=True)

    joblib.dump(model, f"{ARTIFACTS_DIR}/regressors/{symbol}_{horizon}d_{model_name}.pkl")

    meta = {
        "symbol": symbol, "model_type": model_name, "scope": scope,
        "rmse": metrics["rmse"], "mae": metrics["mae"], "r2": metrics["r2"],
        "n_samples": n_samples, "feature_names": FEATURE_COLS,
        "trained_at": str(date.today()), "horizon_days": horizon,
    }
    with open(f"{ARTIFACTS_DIR}/metadata/{symbol}_{horizon}d_regressor.json", "w") as f:
        json.dump(meta, f, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Parse optional --horizon flag: e.g. --horizon 5 or --horizon 1,5,14,30
    horizons_to_train = HORIZONS
    if "--horizon" in sys.argv:
        idx = sys.argv.index("--horizon")
        if idx + 1 < len(sys.argv):
            horizons_to_train = [int(h) for h in sys.argv[idx + 1].split(",")]
            print(f"Training horizons: {horizons_to_train}")

    print("Loading training data...")
    df = load_training_data()
    print(f"Total rows: {len(df):,}  |  Tickers: {df['symbol'].nunique()}")

    for horizon in horizons_to_train:
        target_col = f"target_{horizon}d"
        return_col = f"future_return_{horizon}d"

        hdf = df.dropna(subset=[target_col, return_col]).reset_index(drop=True)
        if len(hdf) < MIN_ROWS:
            print(f"\n── Skipping {horizon}d horizon (only {len(hdf)} rows) ──")
            continue

        X_all = hdf[FEATURE_COLS].reset_index(drop=True)
        y_cls = hdf[target_col].reset_index(drop=True)
        y_reg = hdf[return_col].reset_index(drop=True)

        # ── Global classifier ──────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  HORIZON: {horizon}d")
        print(f"{'='*60}")

        print(f"\n── Global Classifier {horizon}d (5-fold CV) ──")
        g_clf_name, g_clf, g_clf_m = train_best_classifier(X_all, y_cls, n_splits=5)
        save_classifier(g_clf, "GLOBAL", g_clf_name, g_clf_m, "global", len(hdf), X_all, horizon)
        print(f"  {g_clf_name:<16} | ROC-AUC: {g_clf_m['roc_auc']:.4f}  Accuracy: {g_clf_m['accuracy']:.4f}")

        # ── Global regressor ───────────────────────────────────────────────
        print(f"\n── Global Regressor {horizon}d (5-fold CV) ──")
        g_reg_name, g_reg, g_reg_m = train_best_regressor(X_all, y_reg, n_splits=5)
        save_regressor(g_reg, "GLOBAL", g_reg_name, g_reg_m, "global", len(hdf), horizon)
        print(f"  {g_reg_name:<16} | RMSE: {g_reg_m['rmse']:.6f}  MAE: {g_reg_m['mae']:.6f}  R²: {g_reg_m['r2']:.4f}")

        # ── Per-ticker ─────────────────────────────────────────────────────
        print(f"\n── Per-Ticker Models {horizon}d (min {MIN_ROWS} rows) ──")
        skipped = 0

        for symbol in sorted(hdf["symbol"].unique()):
            tk = hdf[hdf["symbol"] == symbol].sort_values("date").reset_index(drop=True)
            if len(tk) < MIN_ROWS:
                skipped += 1
                continue

            X_t     = tk[FEATURE_COLS]
            y_cls_t = tk[target_col]
            y_reg_t = tk[return_col]

            # Classifier
            t_clf_name, t_clf, t_clf_m = train_best_classifier(X_t, y_cls_t, n_splits=3)
            save_classifier(t_clf, symbol, t_clf_name, t_clf_m, "per_ticker", len(tk), X_t, horizon)

            # Regressor
            t_reg_name, t_reg, t_reg_m = train_best_regressor(X_t, y_reg_t, n_splits=3)
            save_regressor(t_reg, symbol, t_reg_name, t_reg_m, "per_ticker", len(tk), horizon)

            print(
                f"  {symbol:<6} | clf: {t_clf_name:<16} AUC={t_clf_m['roc_auc']:.3f} Acc={t_clf_m['accuracy']:.3f}"
                f" | reg: {t_reg_name:<18} RMSE={t_reg_m['rmse']:.5f} MAE={t_reg_m['mae']:.5f} R²={t_reg_m['r2']:.3f}"
            )

        print(f"\nSkipped {skipped} tickers with < {MIN_ROWS} rows for {horizon}d horizon.")

    print("\nDone. Artifacts saved to models/artifacts/")
