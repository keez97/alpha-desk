/**
 * Cross-Asset Pulse — SPY, TLT, GLD, DXY, HYG with sparklines + daily change.
 * Confirms regime signal across asset classes.
 */
import { useQuery } from '@tanstack/react-query';
import api from '../../lib/api';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

interface AssetPulse {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  sparkline: number[];
}

async function fetchCrossAssetPulse(): Promise<AssetPulse[]> {
  const { data } = await api.get('/cross-asset-pulse');
  const raw = data.data || data.assets || data;
  if (!Array.isArray(raw)) return [];
  return raw.map((a: any) => ({
    ticker: a.ticker || '',
    name: a.name || a.ticker || '',
    price: a.price ?? 0,
    change: a.change ?? a.daily_change ?? 0,
    changePct: a.change_pct ?? a.daily_pct_change ?? 0,
    sparkline: a.sparkline || a.history || [],
  }));
}

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 60;
  const h = 20;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={w} height={h} className="shrink-0" aria-hidden="true">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

export function CrossAssetPulsePanel() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['cross-asset-pulse'],
    queryFn: fetchCrossAssetPulse,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  if (isLoading) return <LoadingState message="Loading cross-asset data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.length === 0) {
    return (
      <div className="p-3">
        <div className="text-xs font-semibold text-neutral-200 mb-2">Cross-Asset Pulse</div>
        <div className="text-xs text-neutral-500 text-center py-4">No data available</div>
      </div>
    );
  }

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-neutral-200">Cross-Asset Pulse</span>
        <span className="text-xs text-neutral-500">5-day</span>
      </div>

      <div className="space-y-2 flex-1">
        {data.map((asset) => {
          const isUp = asset.changePct >= 0;
          const color = isUp ? '#4ade80' : '#f87171';
          const arrow = isUp ? '▲' : '▼';
          return (
            <div
              key={asset.ticker}
              className="flex items-center justify-between gap-2 py-1.5 border-b border-neutral-800/50 last:border-0"
            >
              <div className="min-w-0 flex-1">
                <div className="text-xs font-medium text-neutral-200">{asset.ticker}</div>
                <div className="text-xs text-neutral-500 truncate">{asset.name}</div>
              </div>
              <MiniSparkline data={asset.sparkline} color={color} />
              <div className="text-right shrink-0">
                <div className="text-xs font-mono text-neutral-300">{asset.price.toFixed(2)}</div>
                <div className={`text-xs font-mono ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                  {arrow} {isUp ? '+' : ''}{asset.changePct.toFixed(2)}%
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
