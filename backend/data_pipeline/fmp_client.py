import os
import requests
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
FMP_API_KEY = os.getenv("FMP_API_KEY")
BASE_URL = "https://financialmodelingprep.com/stable"

def get_latest_eod_prices(ticker: str, days_back: int = 30, sleep_sec: float = 1.5):
    """
    Fetch the last N days of EOD prices for a symbol.
    Endpoint: /stable/historical-price-eod/full?symbol={ticker}&from={from}&to={to}&apikey={key}
    """
    today = datetime.utcnow().date()
    from_date = (today - timedelta(days=days_back)).isoformat()
    to_date = today.isoformat()

    url = f"{BASE_URL}/historical-price-eod/full"
    params = {
        "symbol": ticker,
        "from": from_date,
        "to": to_date,
        "apikey": FMP_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "historical" in data:
            data = data["historical"]
        time.sleep(sleep_sec)
        return data or []
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        time.sleep(sleep_sec)
        return []