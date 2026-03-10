'use client';

import { useState, useEffect } from 'react';
import { useIntradayMomentum, useScanIntradayMomentum, type IntradaySignal } from '../../hooks/useIntradayMomentum';

interface IntradayMomentumProps {
  interval?: '5m' | '15m';
  benchmark?: string;
  weeks?: number;
  autoRefreshInterval?: number; // milliseconds, 0 to disable
}

function SignalCard({ signal }: { signal: IntradaySignal }) {
  // Color coding: green for breakout, neutral for non-breakout
  const cardBg = signal.isBreakout
    ? 'border-green-800 bg-green-900 bg-opacity-10'
    : 'border-neutral-700 bg-neutral-900 bg-opacity-50';

  const textColor = signal.isBreakout ? 'text-green-400' : 'text-neutral-400';

  return (
    <div className={`border rounded p-3 transition-all ${cardBg}`}>
      {/* Header: Ticker and Sector */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-neutral-200">
            {signal.ticker}
          </h4>
          <span className="text-xs text-neutral-500">{signal.sector}</span>
        </div>
        {/* Interval badge */}
        <span
          className={`text-[10px] px-2 py-0.5 rounded font-medium ${
            signal.interval === '5m'
              ? 'bg-blue-900 bg-opacity-30 text-blue-300 border border-blue-800'
              : 'bg-purple-900 bg-opacity-30 text-purple-300 border border-purple-800'
          }`}
        >
          {signal.interval}
        </span>
      </div>

      {/* Breakout Badge */}
      {signal.isBreakout && (
        <div className="mb-2">
          <span className="inline-block text-[10px] px-2 py-0.5 rounded font-medium bg-green-900 bg-opacity-30 text-green-300 border border-green-800">
            BREAKOUT
          </span>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 text-[10px] pb-2 border-b border-neutral-700 border-opacity-30">
        <div>
          <span className="text-neutral-600">Momentum:</span>
          <span className={`ml-1 font-semibold ${textColor}`}>
            {signal.momentum.toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="text-neutral-600">Volume Surge:</span>
          <span className={`ml-1 font-semibold ${textColor}`}>
            {signal.volumeSurge.toFixed(2)}x
          </span>
        </div>
        <div>
          <span className="text-neutral-600">VWAP Dev:</span>
          <span className={`ml-1 font-semibold ${textColor}`}>
            {signal.vwapDeviation.toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="text-neutral-600">Price:</span>
          <span className="ml-1 text-neutral-300">
            ${signal.price.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Timestamp */}
      <div className="pt-2 text-[10px] text-neutral-500">
        {signal.timestamp && !isNaN(new Date(signal.timestamp).getTime())
          ? new Date(signal.timestamp).toLocaleTimeString()
          : 'Just now'}
      </div>
    </div>
  );
}

export function IntradayMomentum({
  interval = '5m',
  benchmark = 'SPY',
  weeks = 10,
  autoRefreshInterval = 60000, // 60 seconds
}: IntradayMomentumProps) {
  const { data, isLoading, error, refetch } = useIntradayMomentum(
    interval,
    benchmark,
    weeks
  );
  const scanMutation = useScanIntradayMomentum();

  // Filter only breakout signals
  const breakoutSignals = (data?.signals || []).filter((s) => s.isBreakout);

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefreshInterval <= 0) return;

    const timer = setInterval(() => {
      refetch();
    }, autoRefreshInterval);

    return () => clearInterval(timer);
  }, [autoRefreshInterval, refetch]);

  const handleScan = () => {
    scanMutation.mutate({ interval, benchmark, weeks });
  };

  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-100">
          Intraday Momentum
        </h3>
        <button
          onClick={handleScan}
          disabled={isLoading || scanMutation.isPending}
          className="px-3 py-1 text-xs font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-700 disabled:text-neutral-500 text-white rounded transition-colors"
        >
          {scanMutation.isPending ? 'Scanning...' : 'Scan'}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400">
          Failed to load intraday momentum signals
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 bg-neutral-800 rounded animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && breakoutSignals.length === 0 && (
        <div className="p-4 text-center text-neutral-400 text-xs">
          No intraday breakouts detected — all quiet
        </div>
      )}

      {/* Signals list */}
      {!isLoading && breakoutSignals.length > 0 && (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {breakoutSignals.map((signal, idx) => (
            <SignalCard
              key={`${signal.ticker}-${signal.interval}-${idx}`}
              signal={signal}
            />
          ))}
        </div>
      )}

      {/* Footer: signal count summary */}
      {!isLoading && breakoutSignals.length > 0 && (
        <div className="pt-2 border-t border-neutral-800 flex gap-4 text-xs text-neutral-400">
          <span>
            Breakouts:{' '}
            <span className="text-green-500 font-semibold">
              {breakoutSignals.length}
            </span>
          </span>
          <span>
            Interval:{' '}
            <span className="text-neutral-300 font-semibold">{interval}</span>
          </span>
          <span>
            Total Scanned:{' '}
            <span className="text-neutral-300 font-semibold">
              {data?.sectors_scanned || 0}
            </span>
          </span>
        </div>
      )}
    </div>
  );
}
