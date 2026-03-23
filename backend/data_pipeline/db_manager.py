import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "../data/stock_latest.db")

def get_connection():
    """Create a DuckDB connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return duckdb.connect(DB_PATH)

def create_table_from_df(con, table_name: str, df: pd.DataFrame):
    """Create a table dynamically using df's columns if it doesn't exist."""
    cols = ", ".join(f'"{c}" VARCHAR' for c in df.columns)
    con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols});")

def upsert_dataframe(table_name: str, df: pd.DataFrame, key_cols: list):
    """Upsert records (insert new, update existing) using DuckDB MERGE."""
    if df.empty:
        return
    con = get_connection()
    create_table_from_df(con, table_name, df)
    con.register("temp_df", df)

    key_expr = " AND ".join([f"target.{k}=src.{k}" for k in key_cols])
    update_expr = ", ".join([f"{c}=src.{c}" for c in df.columns if c not in key_cols])

    con.execute(f"""
        MERGE INTO {table_name} AS target
        USING temp_df AS src
        ON {key_expr}
        WHEN MATCHED THEN UPDATE SET {update_expr}
        WHEN NOT MATCHED THEN INSERT *;
    """)
    con.close()