'use client';

import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';

type Driver = { feature: string; importance: number };

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'];

export function ShapChart({ drivers }: { drivers: Driver[] }) {
  if (!drivers || drivers.length === 0) {
    return (
      <p className="text-zinc-600 text-sm text-center py-8">
        SHAP data not available for this ticker.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={drivers}
        layout="vertical"
        margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
      >
        <XAxis
          type="number"
          tick={{ fill: '#71717a', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="feature"
          tick={{ fill: '#a1a1aa', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={110}
        />
        <Tooltip
          contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8 }}
          labelStyle={{ color: '#a1a1aa', fontSize: 12 }}
          itemStyle={{ color: '#fff', fontSize: 12 }}
          formatter={(val?: number) => [(val ?? 0).toFixed(6), 'Importance']}
        />
        <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
          {drivers.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
