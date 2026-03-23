import pandas as pd
import time
from data_pipeline.fmp_client import get_latest_eod_prices
from data_pipeline.db_manager import upsert_dataframe

TICKERS = [
    "ADBE", "BAC", "META", "PYPL", "CSCO", "CVX", "UAL", "AAPL", "TSLA", 
    "JPM", "HCA", "DIS","XOM", "F", "TWTR", "NFLX", "PEP", "COST", "T", 
    "VZ", "AAL", "AMZN", "INTC", "C", "SBUX", "GM","DAL", "NKE", "RBLX", 
    "ABBV", "V", "WMT", "BA", "SHOP", "UBER", "KO", "FDX", "LMT", "PLTR", 
    "UNH","PFE", "NVDA", "GE", "GS", "DOCU", "JNJ", "PINS", "WFC", "SNAP", 
    "AMD", "ZM", "MSFT", "TGT", "ROKU", "CCL", "ETSY", "WBA", "COST", "PEP", 
    "KO"
]

def fetch_and_upsert_latest(ticker: str, limit: int = 30):
    """Fetch and upsert latest records for a ticker."""
    print(f"Fetching latest {limit} records for {ticker}")
    raw = get_latest_eod_prices(ticker, limit)
    if not raw:
        print(f"No data for {ticker}")
        return
    df = pd.DataFrame(raw)
    df["symbol"] = ticker
    upsert_dataframe("eod_prices_clean", df, ["symbol", "date"])
    print(f"Upserted {len(df)} records for {ticker}")

if __name__ == "__main__":
    start_time = time.time()
    for idx, t in enumerate(TICKERS, 1):
        try:
            fetch_and_upsert_latest(t, limit=30)
        except Exception as e:
            print(f"{t} failed: {e}")
        print(f"Progress: {idx}/{len(TICKERS)}")
    elapsed = round(time.time() - start_time, 2)
    print(f"\nCompleted {len(TICKERS)} tickers in {elapsed} seconds")