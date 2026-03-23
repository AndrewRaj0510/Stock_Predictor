# Stock Predictor

A full-stack stock prediction platform that fetches market data, engineers features, trains ML models, and serves predictions through a dashboard.

**Data Flow:** FMP API → DuckDB → Feature Engineering → ML Training → FastAPI → Next.js Dashboard

## Tech Stack

| Layer | Tools |
|-------|-------|
| **Data Ingestion** | Financial Modeling Prep (FMP) API, Pandas |
| **Database** | DuckDB (lightweight, embedded OLAP) |
| **ML Models** | Scikit-learn (Logistic Regression, Random Forest), XGBoost, Facebook Prophet, PyTorch |
| **Explainability** | SHAP (feature importance per prediction) |
| **Backend API** | FastAPI + Uvicorn |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **Charting** | Chart.js 4 (react-chartjs-2), Recharts 3 |

## Supported Tickers

60 stocks tracked including AAPL, MSFT, NVDA, TSLA, AMZN, META, GOOGL, JPM, BA, NFLX, DIS, and more. Full list in `backend/data_pipeline/fetch_and_store.py`.

## Project Structure

```
Stock_Predictor/
├── backend/
│   ├── main.py                      # FastAPI server (predictions API)
│   ├── main_training_pipeline.py    # Full ML training pipeline
│   ├── data_pipeline/
│   │   ├── fmp_client.py            # FMP API client
│   │   ├── db_manager.py            # DuckDB upsert logic
│   │   ├── fetch_and_store.py       # Fetch EOD prices → DB
│   │   ├── update_features.py       # Rebuild model_features table
│   │   └── update_targets.py        # Rebuild model_targets table
│   ├── features/
│   │   ├── feature_builder.py       # Log returns, SMAs, volatility, volume stats
│   │   ├── feature_config.py        # Feature definitions
│   │   └── target_builder.py        # 1d/5d/14d/30d future returns + signals
│   ├── models/
│   │   ├── artifacts/               # Saved model files (.pkl) and metadata
│   │   ├── ensemble/                # Ensemble prediction logic
│   │   ├── explainability/          # SHAP explainer
│   │   ├── inference/               # Model loading and prediction
│   │   └── train/                   # Training modules
│   ├── validation/
│   │   ├── backtest.py              # Backtesting framework
│   │   ├── metrics.py               # Evaluation metrics
│   │   └── timeseries_split.py      # Time series cross-validation
│   └── config/                      # YAML config files
├── frontend/
│   └── src/
│       ├── app/                     # Next.js App Router pages
│       ├── components/              # React components
│       └── lib/                     # Utilities and API client
├── data/
│   └── stock_latest.db             # DuckDB database
└── notebooks/                      # Jupyter notebooks for exploration
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Financial Modeling Prep](https://financialmodelingprep.com/) API key

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# or
venv\Scripts\activate          # Windows cmd/PowerShell

# Install dependencies
pip install -r requirements.txt
```

Create `backend/.env`:

```env
FMP_API_KEY=your_fmp_api_key_here
DB_PATH=../data/stock_latest.db
LLM_API_URL=               # Optional: LLM API endpoint
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Running the Platform

### Daily Operations (run every trading day)

These keep your data and features current:

```bash
cd backend
venv\scripts\Activate

# 1. Fetch latest EOD prices from FMP API
python data_pipeline/fetch_and_store.py

# 2. Recompute features (log returns, SMAs, volatility, etc.)
python data_pipeline/update_features.py

# 3. Recompute prediction targets
python data_pipeline/update_targets.py
```

### Weekly Operations (run once a week, e.g., weekends)

Model retraining is compute-intensive and doesn't need to happen daily:

```bash
cd backend
venv\scripts\Activate

# Retrain all models (5-fold time series CV across all tickers)
python main_training_pipeline.py
```

This runs Logistic Regression, Random Forest, and XGBoost classifiers with 5-fold time series cross-validation, and saves trained artifacts to `models/artifacts/`.

### Start the Servers

**Backend** (runs on port 8000):

```bash
cd backend
source venv/Scripts/activate
python main.py
```

**Frontend** (runs on port 3000):

```bash
cd frontend
npm run dev
```

Visit `http://localhost:3000` for the dashboard, or `http://localhost:8000/docs` for the interactive API docs.

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/predictions` | All stocks with signal + confidence (sortable, filterable by horizon) |
| `GET` | `/api/predictions/{symbol}` | Single stock prediction with SHAP explanation |
| `GET` | `/api/historical/{symbol}` | OHLCV price history (7–365 days) |
| `GET` | `/api/features/{symbol}` | Latest computed feature values |
| `GET` | `/api/symbols` | All tracked tickers with company names |
| `GET` | `/api/health` | DB status, model freshness, last update time |
| `POST` | `/api/cache/clear` | Force-clear prediction cache |

### Prediction Response Example

```json
{
  "symbol": "AAPL",
  "signal": "BUY",
  "confidence": 0.74,
  "predicted_return_5d": 0.031,
  "current_price": 182.50,
  "change_1d_pct": 1.2,
  "top_drivers": ["momentum_5d", "price_vs_sma20", "volume_ratio"],
  "model": "xgboost",
  "trained_at": "2026-03-16"
}
```

## ML Pipeline Details

- **Feature Engineering:** Log returns, simple moving averages (SMA5/10/20/50), rolling volatility, volume ratios, price-to-SMA ratios
- **Targets:** Binary classification signals for 1-day, 5-day, 14-day, and 30-day horizons
- **Models:** Per-ticker models for accuracy + a global fallback model for tickers with limited data
- **Validation:** 5-fold time series cross-validation (no data leakage)
- **Explainability:** SHAP values identify the top feature drivers behind each prediction

## Database

DuckDB stores all data in a single file (`data/stock_latest.db`):

| Table | Description |
|-------|-------------|
| `eod_prices_clean` | End-of-day OHLCV prices (primary key: symbol, date) |
| `model_features` | Computed features per ticker per date |
| `model_targets` | Prediction targets per ticker per date |

## Screenshots
<img width="1918" height="860" alt="image" src="https://github.com/user-attachments/assets/5ee94202-e89b-4f75-b86c-0ee3a7630fad" />
<img width="1918" height="867" alt="image" src="https://github.com/user-attachments/assets/6f96cdb3-ace3-4c8e-8ff9-d1ac6b12c567" />


