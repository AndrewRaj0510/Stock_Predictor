import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.feature_builder import build_model_features


if __name__ == "__main__":
    DB_PATH = os.path.join(os.getcwd(), "../data/stock_latest.db")  # adjust if needed

    build_model_features(DB_PATH)