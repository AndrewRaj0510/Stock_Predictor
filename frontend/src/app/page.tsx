'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { getAllPredictions } from '@/lib/api';
import { StockCard, type Prediction } from '@/components/StockCard';

type Filter = 'All' | 'BUY' | 'HOLD' | 'SELL';
const FILTERS: Filter[] = ['All', 'BUY', 'HOLD', 'SELL'];
const HORIZONS = [1, 5, 14, 30] as const;

const SORT_OPTIONS = [
  { value: 'confidence', label: 'Confidence' },
  { value: 'change_1d_pct', label: '1d Change' },
  { value: 'symbol', label: 'A–Z' },
] as const;

export default function DashboardPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>('All');
  const [horizon, setHorizon] = useState(5);
  const [sort, setSort] = useState('confidence');
  const [search, setSearch] = useState('');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [sortOpen, setSortOpen] = useState(false);
  const sortRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (sortRef.current && !sortRef.current.contains(e.target as Node)) setSortOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const fetchPredictions = useCallback(async () => {
    try {
      const data = await getAllPredictions(sort, horizon);
      setPredictions(data.predictions ?? []);
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch {
      setError('Cannot reach the API. Make sure the backend is running on port 8000.');
    } finally {
      setLoading(false);
    }
  }, [sort, horizon]);

  // Initial fetch + 5-min auto-refresh
  useEffect(() => {
    setLoading(true);
    fetchPredictions();
    const interval = setInterval(fetchPredictions, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchPredictions]);

  const filtered = predictions
    .filter(p => !p.error)
    .filter(p => filter === 'All' || p.signal === filter)
    .filter(p => p.symbol.toUpperCase().includes(search.toUpperCase().trim()));

  const counts = {
    BUY: predictions.filter(p => p.signal === 'BUY').length,
    HOLD: predictions.filter(p => p.signal === 'HOLD').length,
    SELL: predictions.filter(p => p.signal === 'SELL').length,
  };

  return (
    <div className="px-4 sm:px-6 py-8 max-w-7xl mx-auto">

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Stock Screener</h1>
          <p className="text-zinc-500 text-sm mt-1">
            {horizon}d horizon ·{' '}
            {lastUpdated ? `Updated at ${lastUpdated}` : 'Loading...'}
          </p>
        </div>

        {/* Summary pills */}
        {!loading && (
          <div className="flex gap-2 text-sm">
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">
              {counts.BUY} BUY
            </span>
            <span className="bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-3 py-1 rounded-full">
              {counts.HOLD} HOLD
            </span>
            <span className="bg-red-500/10 text-red-400 border border-red-500/20 px-3 py-1 rounded-full">
              {counts.SELL} SELL
            </span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {/* Signal filter tabs */}
        <div className="flex bg-zinc-900 border border-zinc-800 rounded-lg p-1 gap-1">
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${filter === f ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white'
                }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Horizon toggle */}
        <div className="flex bg-zinc-900 border border-zinc-800 rounded-lg p-1 gap-1">
          {HORIZONS.map(h => (
            <button
              key={h}
              onClick={() => { setHorizon(h); setLoading(true); }}
              className={`px-2.5 py-1.5 rounded-md text-sm font-medium transition-colors ${horizon === h ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white'
                }`}
            >
              {h}d
            </button>
          ))}
        </div>

        {/* Sort */}
        <div className="relative" ref={sortRef}>
          <button
            onClick={() => setSortOpen(o => !o)}
            className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 text-zinc-300 text-sm rounded-lg px-3 py-2 hover:border-zinc-600 hover:text-white transition-all"
          >
            <svg className="w-3.5 h-3.5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h6M3 12h10M3 17h14" />
            </svg>
            {SORT_OPTIONS.find(o => o.value === sort)?.label}
            <svg className={`w-3 h-3 text-zinc-500 transition-transform ${sortOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {sortOpen && (
            <div className="absolute top-full left-0 mt-1 w-40 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl shadow-black/40 overflow-hidden z-30 animate-in fade-in slide-in-from-top-1">
              {SORT_OPTIONS.map(o => (
                <button
                  key={o.value}
                  onClick={() => { setSort(o.value); setSortOpen(false); }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors ${sort === o.value
                      ? 'bg-zinc-800 text-white'
                      : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-white'
                    }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Search */}
        <input
          type="text"
          placeholder="Search ticker..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-zinc-900 border border-zinc-800 text-zinc-300 placeholder-zinc-600 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-600 w-36"
        />

        <span className="text-zinc-600 text-sm ml-auto">
          {filtered.length} stocks
        </span>

        <button
          onClick={() => { setLoading(true); fetchPredictions(); }}
          className="text-sm text-zinc-400 hover:text-white border border-zinc-800 hover:border-zinc-600 px-3 py-1.5 rounded-lg transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-950/50 border border-red-800 text-red-300 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 h-40 animate-pulse" />
          ))}
        </div>
      )}

      {/* Cards grid */}
      {!loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {filtered.map(p => <StockCard key={p.symbol} p={p} />)}
          {filtered.length === 0 && (
            <p className="col-span-full text-center text-zinc-600 py-16">
              No stocks match the current filter.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
