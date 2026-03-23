import Link from 'next/link';
import { SignalBadge } from './SignalBadge';

export type Prediction = {
  symbol: string;
  name?: string;
  signal: string;
  confidence: number;
  predicted_return_pct: number | null;
  horizon_days: number;
  current_price: number | null;
  change_1d_pct: number | null;
  as_of_date: string;
  error?: string;
};

const barColor: Record<string, string> = {
  BUY:  'bg-emerald-500',
  SELL: 'bg-red-500',
  HOLD: 'bg-yellow-500',
};

const glowColor: Record<string, string> = {
  BUY:  'hover:shadow-emerald-500/10',
  SELL: 'hover:shadow-red-500/10',
  HOLD: 'hover:shadow-yellow-500/10',
};

const borderGlow: Record<string, string> = {
  BUY:  'hover:border-emerald-500/30',
  SELL: 'hover:border-red-500/30',
  HOLD: 'hover:border-yellow-500/30',
};

export function StockCard({ p }: { p: Prediction }) {
  if (p.error) {
    return (
      <div className="bg-zinc-900/60 border border-zinc-800/50 rounded-2xl p-4 opacity-40 backdrop-blur-sm">
        <span className="text-white font-bold">{p.symbol}</span>
        <p className="text-zinc-600 text-xs mt-1 truncate">No data</p>
      </div>
    );
  }

  const changePositive = (p.change_1d_pct ?? 0) >= 0;
  const predPositive   = (p.predicted_return_pct ?? 0) >= 0;

  // Display confidence as signal strength (always 0–1 towards the signal direction)
  const signalConfidence = p.signal === 'SELL' ? 1 - p.confidence : p.confidence;
  const pct = Math.round(signalConfidence * 100);

  return (
    <Link href={`/stock/${p.symbol}`}>
      <div className={`
        group relative bg-zinc-900/70 border border-zinc-800/60 rounded-2xl p-4
        backdrop-blur-sm cursor-pointer h-full
        transition-all duration-300 ease-out
        hover:-translate-y-1 hover:shadow-lg
        ${glowColor[p.signal] ?? 'hover:shadow-zinc-500/10'}
        ${borderGlow[p.signal] ?? 'hover:border-zinc-600'}
        hover:bg-zinc-800/40
      `}>

        {/* Subtle top-edge gradient accent on hover */}
        <div className={`absolute inset-x-0 top-0 h-px rounded-t-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
          p.signal === 'BUY' ? 'bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent' :
          p.signal === 'SELL' ? 'bg-gradient-to-r from-transparent via-red-500/50 to-transparent' :
          'bg-gradient-to-r from-transparent via-yellow-500/50 to-transparent'
        }`} />

        {/* Ticker + Signal */}
        <div className="flex items-start justify-between mb-3">
          <div className="min-w-0 mr-2">
            <span className="text-white font-bold text-lg group-hover:text-zinc-100 transition-colors">{p.symbol}</span>
            {p.name && (
              <span className="text-zinc-500 text-xs ml-1.5 truncate">({p.name})</span>
            )}
          </div>
          <SignalBadge signal={p.signal} />
        </div>

        {/* Price + 1d change */}
        <div className="mb-3">
          <span className="text-white text-xl font-semibold">
            {p.current_price != null ? `$${p.current_price.toFixed(2)}` : '—'}
          </span>
          {p.change_1d_pct != null && (
            <span className={`ml-2 text-sm font-medium ${changePositive ? 'text-emerald-400' : 'text-red-400'}`}>
              {changePositive ? '+' : ''}{p.change_1d_pct}%
            </span>
          )}
        </div>

        {/* Confidence bar */}
        <div className="mb-2">
          <div className="flex justify-between text-xs text-zinc-500 mb-1">
            <span>Confidence</span>
            <span>{pct}%</span>
          </div>
          <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 group-hover:brightness-110 ${barColor[p.signal] ?? 'bg-zinc-500'}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Predicted return */}
        {p.predicted_return_pct != null && (
          <div className={`text-xs mt-2 font-medium ${predPositive ? 'text-emerald-400' : 'text-red-400'}`}>
            {predPositive ? '+' : ''}{p.predicted_return_pct.toFixed(2)}% predicted · {p.horizon_days ?? 5}d
          </div>
        )}
      </div>
    </Link>
  );
}
