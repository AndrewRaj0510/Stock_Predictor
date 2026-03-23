import duckdb
import os


def build_model_targets(db_path: str):
    """
    Rebuilds model_targets table with multi-horizon regression
    and classification targets.
    """

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = duckdb.connect(database=db_path, read_only=False)

    print("Rebuilding model_targets table...")

    conn.execute("""
    DROP TABLE IF EXISTS model_targets;

    CREATE TABLE model_targets AS

    WITH future_returns AS (
        SELECT
            symbol,
            date,
            close,

            (LEAD(close, 1) OVER (
                PARTITION BY symbol ORDER BY date
            ) / close - 1) AS future_return_1d,

            (LEAD(close, 5) OVER (
                PARTITION BY symbol ORDER BY date
            ) / close - 1) AS future_return_5d,

            (LEAD(close, 14) OVER (
                PARTITION BY symbol ORDER BY date
            ) / close - 1) AS future_return_14d,

            (LEAD(close, 30) OVER (
                PARTITION BY symbol ORDER BY date
            ) / close - 1) AS future_return_30d

        FROM eod_prices_clean
    )

    SELECT
        symbol,
        date,

        future_return_1d,
        future_return_5d,
        future_return_14d,
        future_return_30d,

        CASE WHEN future_return_1d > 0 THEN 1 ELSE 0 END AS target_1d,
        CASE WHEN future_return_5d > 0 THEN 1 ELSE 0 END AS target_5d,
        CASE WHEN future_return_14d > 0 THEN 1 ELSE 0 END AS target_14d,
        CASE WHEN future_return_30d > 0 THEN 1 ELSE 0 END AS target_30d

    FROM future_returns;
    """)

    conn.close()

    print("model_targets table rebuilt successfully.")