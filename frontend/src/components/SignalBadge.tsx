type Signal = 'BUY' | 'HOLD' | 'SELL';

const styles: Record<Signal, string> = {
  BUY:  'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  SELL: 'bg-red-500/20 text-red-400 border border-red-500/30',
  HOLD: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
};

export function SignalBadge({ signal }: { signal: string }) {
  const s = (signal as Signal) in styles ? (signal as Signal) : 'HOLD';
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold tracking-wide ${styles[s]}`}>
      {signal}
    </span>
  );
}
