'use client';

import { useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

type PricePoint = { date: string; close: number };

const RANGES = [
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '1y',  days: 365 },
] as const;

export function PriceChart({ prices, symbol }: { prices: PricePoint[]; symbol: string }) {
  const [range, setRange] = useState(90);

  const sliced = useMemo(() => prices.slice(-range), [prices, range]);

  const isPositive = sliced.length >= 2 && sliced[sliced.length - 1].close >= sliced[0].close;
  const lineColor  = isPositive ? '#10b981' : '#ef4444';
  const fillColor  = isPositive ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)';

  const data = {
    labels: sliced.map(p => p.date),
    datasets: [{
      data: sliced.map(p => p.close),
      borderColor: lineColor,
      backgroundColor: fillColor,
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 4,
      borderWidth: 2,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: (items: any[]) => items[0].label,
          label: (ctx: any) => ` $${ctx.parsed.y.toFixed(2)}`,
        },
        backgroundColor: '#18181b',
        borderColor: '#3f3f46',
        borderWidth: 1,
        titleColor: '#a1a1aa',
        bodyColor: '#ffffff',
      },
    },
    scales: {
      x: {
        grid: { color: '#27272a' },
        ticks: { color: '#71717a', maxTicksLimit: 7, font: { size: 11 } },
        border: { color: '#27272a' },
      },
      y: {
        grid: { color: '#27272a' },
        ticks: {
          color: '#71717a',
          font: { size: 11 },
          callback: (v: any) => `$${Number(v).toFixed(0)}`,
        },
        border: { color: '#27272a' },
      },
    },
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-semibold">Price History — {symbol}</h2>
        <div className="flex bg-zinc-900 border border-zinc-800 rounded-lg p-1 gap-1">
          {RANGES.map(r => (
            <button
              key={r.days}
              onClick={() => setRange(r.days)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                range === r.days ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-white'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div style={{ height: 300 }}>
        <Line data={data} options={options as any} />
      </div>
    </div>
  );
}
