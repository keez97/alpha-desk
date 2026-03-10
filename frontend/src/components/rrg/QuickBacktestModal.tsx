import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import api from '../../lib/api';
import type { TradeIdea } from '../../hooks/useQuickBacktest';

interface QuickBacktestModalProps {
  tradeIdea: TradeIdea;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (backtestId: number) => void;
}

export function QuickBacktestModal({
  tradeIdea,
  isOpen,
  onClose,
  onSuccess,
}: QuickBacktestModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const config = tradeIdea.backtestConfig;

  // Create backtest mutation
  const createBacktestMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/backtests', {
        name: data.name,
        start_date: data.start_date,
        end_date: data.end_date,
        rebalance_frequency: data.rebalance_frequency,
        universe_selection: data.universe_selection,
        commission_bps: data.transaction_costs.commission_bps,
        slippage_bps: data.transaction_costs.slippage_bps,
        factor_allocations: data.factor_allocations,
      });
      return response.data;
    },
  });

  // Run backtest mutation
  const runBacktestMutation = useMutation({
    mutationFn: async (backtestId: number) => {
      const response = await api.post(`/backtests/${backtestId}/run`);
      return response.data;
    },
  });

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      // Create backtest with configuration
      const createdBacktest = await createBacktestMutation.mutateAsync(config);

      if (!createdBacktest.id) {
        throw new Error('No backtest ID returned');
      }

      // Run the backtest
      await runBacktestMutation.mutateAsync(createdBacktest.id);

      // Success - close modal and notify parent
      onSuccess?.(createdBacktest.id);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create backtest';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-neutral-900 border border-neutral-700 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-xl">
        {/* Header */}
        <div className="sticky top-0 bg-neutral-900 border-b border-neutral-800 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-200">
            Quick Backtest: {tradeIdea.ticker}
          </h2>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Trade Thesis */}
          <div>
            <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2">
              Trade Thesis
            </h3>
            <div className="bg-neutral-950 border border-neutral-800 rounded p-3">
              <p className="text-sm text-neutral-300 leading-relaxed">
                {tradeIdea.thesis}
              </p>
              <div className="mt-3 flex items-center gap-4 text-xs">
                <div>
                  <span className="text-neutral-500">Quadrant:</span>
                  <span className="ml-2 text-neutral-300 font-medium">
                    {tradeIdea.quadrant}
                  </span>
                </div>
                <div>
                  <span className="text-neutral-500">Direction:</span>
                  <span
                    className={`ml-2 font-medium ${
                      tradeIdea.direction === 'long'
                        ? 'text-green-400'
                        : tradeIdea.direction === 'short'
                          ? 'text-red-400'
                          : 'text-neutral-400'
                    }`}
                  >
                    {tradeIdea.direction.toUpperCase()}
                  </span>
                </div>
                <div>
                  <span className="text-neutral-500">Confidence:</span>
                  <span
                    className={`ml-2 font-medium ${
                      tradeIdea.confidence === 'high'
                        ? 'text-green-400'
                        : tradeIdea.confidence === 'medium'
                          ? 'text-yellow-400'
                          : 'text-orange-400'
                    }`}
                  >
                    {tradeIdea.confidence.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* RRG Metrics */}
          <div>
            <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2">
              RRG Metrics
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-neutral-950 border border-neutral-800 rounded p-3">
                <div className="text-xs text-neutral-500 mb-1">RS-Ratio</div>
                <div className="text-lg font-semibold text-neutral-200">
                  {tradeIdea.rsRatio.toFixed(2)}
                </div>
              </div>
              <div className="bg-neutral-950 border border-neutral-800 rounded p-3">
                <div className="text-xs text-neutral-500 mb-1">RS-Momentum</div>
                <div className="text-lg font-semibold text-neutral-200">
                  {tradeIdea.rsMomentum.toFixed(2)}
                </div>
              </div>
            </div>
          </div>

          {/* Backtest Configuration */}
          <div>
            <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2">
              Backtest Configuration
            </h3>
            <div className="space-y-3 bg-neutral-950 border border-neutral-800 rounded p-4">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-neutral-500">Start Date:</span>
                  <div className="text-neutral-300 font-medium mt-1">
                    {config.start_date}
                  </div>
                </div>
                <div>
                  <span className="text-neutral-500">End Date:</span>
                  <div className="text-neutral-300 font-medium mt-1">
                    {config.end_date}
                  </div>
                </div>
                <div>
                  <span className="text-neutral-500">Rebalance:</span>
                  <div className="text-neutral-300 font-medium mt-1">
                    {config.rebalance_frequency}
                  </div>
                </div>
                <div>
                  <span className="text-neutral-500">Universe:</span>
                  <div className="text-neutral-300 font-medium mt-1">
                    {config.universe_selection}
                  </div>
                </div>
              </div>

              <div className="border-t border-neutral-700 pt-3">
                <div className="text-xs text-neutral-500 mb-2">Transaction Costs:</div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-neutral-600">Commission:</span>
                    <span className="ml-2 text-neutral-300">
                      {config.transaction_costs.commission_bps} bps
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-600">Slippage:</span>
                    <span className="ml-2 text-neutral-300">
                      {config.transaction_costs.slippage_bps} bps
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-900 bg-opacity-20 border border-red-800 rounded p-3">
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-neutral-900 border-t border-neutral-800 px-6 py-4 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm text-neutral-400 hover:text-neutral-200 border border-neutral-700 hover:border-neutral-600 transition-colors"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-2 rounded text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-700 text-white transition-colors"
          >
            {isSubmitting ? 'Creating...' : 'Create & Run Backtest'}
          </button>
        </div>
      </div>
    </div>
  );
}
