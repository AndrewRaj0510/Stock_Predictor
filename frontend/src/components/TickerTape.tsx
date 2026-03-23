'use client';

import { useEffect, useRef } from 'react';

export function TickerTape() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    // Clear any previous widget
    containerRef.current.innerHTML = '';

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js';
    script.async = true;
    script.type = 'text/javascript';
    script.innerHTML = JSON.stringify({
      symbols: [
        { proName: 'NASDAQ:ADBE', title: 'Adobe' },
        { proName: 'NYSE:BAC', title: 'BofA' },
        { proName: 'NASDAQ:META', title: 'Meta' },
        { proName: 'NASDAQ:PYPL', title: 'PayPal' },
        { proName: 'NASDAQ:CSCO', title: 'Cisco' },
        { proName: 'NYSE:CVX', title: 'Chevron' },
        { proName: 'NASDAQ:UAL', title: 'United Air' },
        { proName: 'NASDAQ:AAPL', title: 'Apple' },
        { proName: 'NASDAQ:TSLA', title: 'Tesla' },
        { proName: 'NYSE:JPM', title: 'JPMorgan' },
        { proName: 'NYSE:HCA', title: 'HCA' },
        { proName: 'NYSE:DIS', title: 'Disney' },
        { proName: 'NYSE:XOM', title: 'Exxon' },
        { proName: 'NYSE:F', title: 'Ford' },
        { proName: 'NASDAQ:NFLX', title: 'Netflix' },
        { proName: 'NASDAQ:PEP', title: 'Pepsi' },
        { proName: 'NASDAQ:COST', title: 'Costco' },
        { proName: 'NYSE:T', title: 'AT&T' },
        { proName: 'NYSE:VZ', title: 'Verizon' },
        { proName: 'NASDAQ:AAL', title: 'American Air' },
        { proName: 'NASDAQ:AMZN', title: 'Amazon' },
        { proName: 'NASDAQ:INTC', title: 'Intel' },
        { proName: 'NYSE:C', title: 'Citi' },
        { proName: 'NASDAQ:SBUX', title: 'Starbucks' },
        { proName: 'NYSE:GM', title: 'GM' },
        { proName: 'NYSE:DAL', title: 'Delta' },
        { proName: 'NYSE:NKE', title: 'Nike' },
        { proName: 'NYSE:RBLX', title: 'Roblox' },
        { proName: 'NYSE:ABBV', title: 'AbbVie' },
        { proName: 'NYSE:V', title: 'Visa' },
        { proName: 'NYSE:WMT', title: 'Walmart' },
        { proName: 'NYSE:BA', title: 'Boeing' },
        { proName: 'NYSE:SHOP', title: 'Shopify' },
        { proName: 'NYSE:UBER', title: 'Uber' },
        { proName: 'NYSE:KO', title: 'Coca-Cola' },
        { proName: 'NYSE:FDX', title: 'FedEx' },
        { proName: 'NYSE:LMT', title: 'Lockheed' },
        { proName: 'NASDAQ:PLTR', title: 'Palantir' },
        { proName: 'NYSE:UNH', title: 'UnitedHealth' },
        { proName: 'NYSE:PFE', title: 'Pfizer' },
        { proName: 'NASDAQ:NVDA', title: 'NVIDIA' },
        { proName: 'NYSE:GE', title: 'GE' },
        { proName: 'NYSE:GS', title: 'Goldman' },
        { proName: 'NASDAQ:DOCU', title: 'DocuSign' },
        { proName: 'NYSE:JNJ', title: 'J&J' },
        { proName: 'NYSE:PINS', title: 'Pinterest' },
        { proName: 'NYSE:WFC', title: 'Wells Fargo' },
        { proName: 'NYSE:SNAP', title: 'Snap' },
        { proName: 'NASDAQ:AMD', title: 'AMD' },
        { proName: 'NASDAQ:ZM', title: 'Zoom' },
        { proName: 'NASDAQ:MSFT', title: 'Microsoft' },
        { proName: 'NYSE:TGT', title: 'Target' },
        { proName: 'NASDAQ:ROKU', title: 'Roku' },
        { proName: 'NYSE:CCL', title: 'Carnival' },
        { proName: 'NASDAQ:ETSY', title: 'Etsy' },
        { proName: 'NASDAQ:WBA', title: 'Walgreens' },
      ],
      showSymbolLogo: true,
      isTransparent: true,
      displayMode: 'adaptive',
      colorTheme: 'dark',
      locale: 'en',
    });

    containerRef.current.appendChild(script);
  }, []);

  return (
    <div className="w-full border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-sm overflow-hidden">
      <div className="tradingview-widget-container" ref={containerRef}>
        <div className="tradingview-widget-container__widget"></div>
      </div>
    </div>
  );
}
