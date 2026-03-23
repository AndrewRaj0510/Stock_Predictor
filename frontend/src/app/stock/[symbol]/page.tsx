'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getPrediction, getHistorical, getFeatures } from '@/lib/api';
import { SignalBadge } from '@/components/SignalBadge';
import { PriceChart } from '@/components/PriceChart';
import { ShapChart } from '@/components/ShapChart';

type Driver   = { feature: string; importance: number };
type PriceRow = { date: string; close: number };

type PredictionDetail = {
  symbol: string;
  name?: string;
  signal: string;
  confidence: number;
  predicted_return_pct: number | null;
  horizon_days: number;
  current_price: number | null;
  change_1d_pct: number | null;
  top_drivers: Driver[];
  model_type: string;
  model_scope: string;
  classifier_metrics: { roc_auc: number; accuracy: number };
  regressor_metrics: { rmse: number; mae: number; r2: number };
  trained_at: string;
  as_of_date: string;
};

const HORIZONS = [1, 5, 14, 30] as const;

type Features = {
  rsi_14: number;
  price_vs_sma20: number;
  volatility_20: number;
  volume_ratio: number;
  ema_diff: number;
  obv_signal: number;
};

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-zinc-800 last:border-0">
      <span className="text-zinc-500 text-sm">{label}</span>
      <span className="text-white text-sm font-medium">{value}</span>
    </div>
  );
}

export default function StockDetailPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = (params.symbol as string).toUpperCase();

  const [pred, setPred]         = useState<PredictionDetail | null>(null);
  const [prices, setPrices]     = useState<PriceRow[]>([]);
  const [features, setFeatures] = useState<Features | null>(null);
  const [horizon, setHorizon]   = useState(5);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  // Load price history + features once
  useEffect(() => {
    async function loadStatic() {
      try {
        const [histData, featData] = await Promise.all([
          getHistorical(symbol, 365),
          getFeatures(symbol),
        ]);
        setPrices(histData.prices ?? []);
        setFeatures(featData.features ?? null);
      } catch (e: any) {
        setError(e?.response?.data?.detail ?? 'Failed to load data.');
      }
    }
    loadStatic();
  }, [symbol]);

  // Load prediction whenever horizon changes
  useEffect(() => {
    async function loadPred() {
      setLoading(true);
      try {
        const predData = await getPrediction(symbol, horizon);
        setPred(predData);
        setError(null);
      } catch (e: any) {
        setError(e?.response?.data?.detail ?? 'Failed to load prediction for this horizon.');
      } finally {
        setLoading(false);
      }
    }
    loadPred();
  }, [symbol, horizon]);

  const changePositive = (pred?.change_1d_pct ?? 0) >= 0;
  const predPositive   = (pred?.predicted_return_pct ?? 0) >= 0;
  const signalConfidence = pred
    ? pred.signal === 'SELL'
      ? Math.round((1 - pred.confidence) * 100)
      : Math.round(pred.confidence * 100)
    : 0;

  const barColor: Record<string, string> = {
    BUY: 'bg-emerald-500', SELL: 'bg-red-500', HOLD: 'bg-yellow-500',
  };

  return (
    <div className="px-4 sm:px-6 py-8 max-w-5xl mx-auto">

      {/* Back + header */}
      <button
        onClick={() => router.back()}
        className="text-zinc-500 hover:text-white text-sm mb-6 flex items-center gap-1 transition-colors"
      >
        ← Back to screener
      </button>

      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl h-32 animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-950/50 border border-red-800 text-red-300 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {!loading && pred && (
        <div className="space-y-6">

          {/* Ticker + price */}
          <div className="flex flex-wrap items-center gap-4">
            <h1 className="text-3xl font-bold text-white">
              {symbol}
              {pred.name && pred.name !== symbol && (
                <span className="text-zinc-500 text-lg font-normal ml-2">({pred.name})</span>
              )}
            </h1>
            {pred.current_price != null && (
              <span className="text-2xl text-zinc-300 font-semibold">
                ${pred.current_price.toFixed(2)}
              </span>
            )}
            {pred.change_1d_pct != null && (
              <span className={`text-lg font-medium ${changePositive ? 'text-emerald-400' : 'text-red-400'}`}>
                {changePositive ? '+' : ''}{pred.change_1d_pct}% today
              </span>
            )}
          </div>

          {/* ── Prediction card ─────────────────────────────────────── */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex flex-wrap items-start gap-6">

              {/* Signal + confidence */}
              <div className="flex-1 min-w-48">
                {/* Horizon toggle */}
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-zinc-500 text-xs uppercase tracking-wider">Signal ·</span>
                  <div className="flex bg-zinc-800 rounded-md p-0.5 gap-0.5">
                    {HORIZONS.map(h => (
                      <button
                        key={h}
                        onClick={() => setHorizon(h)}
                        className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                          horizon === h ? 'bg-zinc-600 text-white' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                        {h}d
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-3 mb-4">
                  <SignalBadge signal={pred.signal} />
                  <span className="text-zinc-400 text-sm">{signalConfidence}% confident</span>
                </div>
                {/* Confidence bar */}
                <div className="h-2 bg-zinc-800 rounded-full overflow-hidden mb-4">
                  <div
                    className={`h-full rounded-full ${barColor[pred.signal] ?? 'bg-zinc-500'}`}
                    style={{ width: `${signalConfidence}%` }}
                  />
                </div>
                {/* Predicted return */}
                {pred.predicted_return_pct != null && (
                  <p className={`text-sm font-medium ${predPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                    Predicted: {predPositive ? '+' : ''}{pred.predicted_return_pct.toFixed(3)}% in {horizon} days
                  </p>
                )}
              </div>

              {/* Classifier metrics */}
              <div className="min-w-40">
                <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Classifier</p>
                <div className="space-y-1 text-sm">
                  <div className="flex gap-2">
                    <span className="text-zinc-500">ROC-AUC</span>
                    <span className="text-white font-medium">{pred.classifier_metrics.roc_auc.toFixed(4)}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-zinc-500">Accuracy</span>
                    <span className="text-white font-medium">{(pred.classifier_metrics.accuracy * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-zinc-500">Model</span>
                    <span className="text-white font-medium capitalize">{pred.model_type?.replace('_', ' ')}</span>
                  </div>
                </div>
              </div>

              {/* Regressor metrics */}
              {pred.regressor_metrics && (
                <div className="min-w-40">
                  <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Regressor</p>
                  <div className="space-y-1 text-sm">
                    <div className="flex gap-2">
                      <span className="text-zinc-500">RMSE</span>
                      <span className="text-white font-medium">{pred.regressor_metrics.rmse?.toFixed(5)}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-zinc-500">MAE</span>
                      <span className="text-white font-medium">{pred.regressor_metrics.mae?.toFixed(5)}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-zinc-500">R²</span>
                      <span className="text-white font-medium">{pred.regressor_metrics.r2?.toFixed(4)}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Meta */}
              <div className="min-w-36 text-sm text-zinc-600 space-y-1 self-end">
                <p>Scope: {pred.model_scope}</p>
                <p>Trained: {pred.trained_at}</p>
                <p>As of: {pred.as_of_date}</p>
              </div>
            </div>
          </div>

          {/* ── Price chart ─────────────────────────────────────────── */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            {prices.length > 0
              ? <PriceChart prices={prices} symbol={symbol} />
              : <p className="text-zinc-600 text-sm text-center py-12">No price history available.</p>
            }
          </div>

          {/* ── SHAP + Key stats ─────────────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* SHAP drivers */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <h2 className="text-white font-semibold mb-4">Why this signal?</h2>
              <ShapChart drivers={pred.top_drivers} />
            </div>

            {/* Key stats */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <h2 className="text-white font-semibold mb-4">Key Indicators</h2>
              {features ? (
                <div>
                  <StatRow
                    label="RSI (14)"
                    value={features.rsi_14 != null
                      ? `${features.rsi_14.toFixed(1)} ${features.rsi_14 > 70 ? '— Overbought' : features.rsi_14 < 30 ? '— Oversold' : ''}`
                      : '—'}
                  />
                  <StatRow
                    label="Price vs SMA20"
                    value={features.price_vs_sma20 != null
                      ? `${features.price_vs_sma20.toFixed(3)}x ${features.price_vs_sma20 > 1 ? '↑ above' : '↓ below'}`
                      : '—'}
                  />
                  <StatRow
                    label="Volatility (20d)"
                    value={features.volatility_20 != null
                      ? `${(features.volatility_20 * 100).toFixed(2)}% daily`
                      : '—'}
                  />
                  <StatRow
                    label="Volume Ratio"
                    value={features.volume_ratio != null
                      ? `${features.volume_ratio.toFixed(2)}x avg`
                      : '—'}
                  />
                  <StatRow
                    label="EMA Diff"
                    value={features.ema_diff != null
                      ? `${features.ema_diff >= 0 ? '+' : ''}${(features.ema_diff * 100).toFixed(3)}%`
                      : '—'}
                  />
                  <StatRow
                    label="OBV Signal"
                    value={features.obv_signal != null
                      ? `${features.obv_signal >= 0 ? '+' : ''}${features.obv_signal.toFixed(2)}`
                      : '—'}
                  />
                </div>
              ) : (
                <p className="text-zinc-600 text-sm">No feature data available.</p>
              )}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
