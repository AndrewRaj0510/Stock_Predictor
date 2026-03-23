import os
import json
import shap
import numpy as np
import pandas as pd

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "../artifacts")


def compute_and_save_shap(symbol: str, model, X_sample: pd.DataFrame,
                          model_type: str) -> list:
    """
    Compute mean absolute SHAP values for a fitted model and save to artifacts/shap/.
    Returns the top-5 feature drivers list.
    """
    os.makedirs(f"{ARTIFACTS_DIR}/shap", exist_ok=True)

    feature_names = list(X_sample.columns)

    try:
        if model_type in ("random_forest", "xgboost"):
            explainer = shap.TreeExplainer(model)
            raw = explainer.shap_values(X_sample)

            # SHAP <0.46: returns list [class0_array, class1_array]
            # SHAP >=0.46: returns 3D array (samples, features, classes) for RF
            #              returns 2D array (samples, features) for XGBoost binary
            if isinstance(raw, list):
                shap_values = raw[1]
            elif hasattr(raw, "ndim") and raw.ndim == 3:
                shap_values = raw[:, :, 1]  # take class 1 = "up"
            else:
                shap_values = raw

        else:  # logistic regression
            explainer = shap.LinearExplainer(model, X_sample, feature_perturbation="interventional")
            shap_values = explainer.shap_values(X_sample)

        # Mean absolute importance per feature
        mean_abs = np.abs(np.array(shap_values)).mean(axis=0)
        importance = dict(zip(feature_names, mean_abs.tolist()))
        sorted_feats = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        top_drivers = [
            {"feature": k, "importance": round(v, 6)}
            for k, v in sorted_feats[:5]
        ]

        payload = {
            "symbol": symbol,
            "top_drivers": top_drivers,
            "all_features": {k: round(v, 6) for k, v in importance.items()},
        }

        with open(f"{ARTIFACTS_DIR}/shap/{symbol}.json", "w") as f:
            json.dump(payload, f, indent=2)

        return top_drivers

    except Exception as e:
        print(f"  [SHAP warning] {symbol}: {e} — skipping SHAP for this ticker")
        return []
