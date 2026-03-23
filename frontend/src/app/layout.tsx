import type { Metadata } from 'next';
import { Geist } from 'next/font/google';
import Link from 'next/link';
import { TickerTape } from '@/components/TickerTape';
import './globals.css';

const geist = Geist({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'StockPredictor',
  description: 'ML-powered stock signal screener — 60 stocks, multi-horizon predictions',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geist.className} bg-zinc-950 text-zinc-50 antialiased`}>
        <nav className="sticky top-0 z-20 border-b border-zinc-800/60 bg-zinc-950/90 backdrop-blur-md px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-white font-bold text-lg tracking-tight hover:text-zinc-300 transition-colors">
            StockPredictor
          </Link>
        </nav>
        <TickerTape />
        <main className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-900 via-zinc-950 to-zinc-950">
          {children}
        </main>
      </body>
    </html>
  );
}
