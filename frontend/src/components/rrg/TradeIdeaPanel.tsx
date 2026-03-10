import { useState } from 'react';
import { useTradeIdeas } from '../../hooks/useQuickBacktest';
import { QuickBacktestModal } from './QuickBacktestModal';
import type { TradeIdea } from '../../hooks/useQuickBacktest';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

interface TradeIdeaPanelProps {
  benchmark?: string;
  weeks?: number;
}

export function TradeIdeaPanel({ benchmark = 'SPY', weeks = 10 }: TradeIdeaPanelProps) {
  const [selectedIdea, setSelectedIdea] = useState<TradeIdea | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: tradeIdeas, isLoading, error, refetch } = useTradeIdeas(
    benchmark,
    weeks,
    true
  );

  const handleBacktestClick = (idea: TradeIdea) => {
    setSelectedIdea(idea);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedIdea(null);
  };

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'long':
        return 'border-green-800 bg-green-900 bg-opacity-10';
      case 'short':
        return 'border-red-800 bg-red-900 bg-opacity-10';
      default:
        return 'border-neutral-700 bg-neutral-900 bg-opacity-50';
    }
  };

  const getDirectionTextColor = (direction: string) => {
    switch (direction) {
      case 'long':
        return 'text-green-400';
      case 'short':
        return 'text-red-400';
      default:
        return 'text-neutral-400';
    }
  };

  const getConfidenceBadgeColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'bg-green-900 bg-opacity-30 text-green-300 border border-green-800';
      case 'medium':
        return 'bg-yellow-900 bg-opacity-30 text-yellow-300 border border-yellow-800';
      default:
        return 'bg-orange-900 bg-opacity-30 text-orange-300 border border-orange-800';
    }
  };

  if (isLoading) {
    return (
      <div className="bg-neutral-950 border border-neutral-800 rounded p-4">
        <LoadingState message="Loading trade ideas..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-neutral-950 border border-neutral-800 rounded p-4">
        <ErrorState error={error} onRetry={() => refetch()} />
      </div>
    );
  }

  if (!tradeIdeas || tradeIdeas.length === 0) {
    return (
      <div className="bg-neutral-950 border border-neutral-800 rounded p-4">
        <p className="text-xs text-neutral-500">No trade ideas available</p>
      </div>
    );
  }

  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded p-4 space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-neutral-200">Trade Ideas</h3>
        <span className="text-xs text-neutral-500">{tradeIdeas.length} sectors</span>
      </div>

      <div className="space-y-2 max-h-[600px] overflow-y-auto">
        {tradeIdeas.map((idea) => (
          <div
            key={idea.ticker}
            className={`border rounded p-3 transition-all hover:border-neutral-600 ${getDirectionColor(
              idea.direction
            )}`}
          >
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-sm font-semibold text-neutral-200">
                    {idea.ticker}
                  </h4>
                  <span className="text-xs text-neutral-500">
                    {idea.sectorName}
                  </span>
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`text-xs font-semibold ${getDirectionTextColor(
                      idea.direction
                    )}`}
                  >
                    {idea.direction === 'long'
                      ? '↑ LONG'
                      : idea.direction === 'short'
                        ? '↓ SHORT'
                        : '⊗ AVOID'}
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded ${getConfidenceBadgeColor(
                      idea.confidence
                    )}`}
                  >
                    {idea.confidence.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>

            {/* RRG Metrics */}
            <div className="grid grid-cols-2 gap-2 text-[10px] mb-2 pb-2 border-b border-neutral-700 border-opacity-30">
              <div>
                <span className="text-neutral-600">RS-Ratio:</span>
                <span className="ml-1 text-neutral-300">
                  {idea.rsRatio.toFixed(1)}
                </span>
              </div>
              <div>
                <span className="text-neutral-600">RS-Mom:</span>
                <span className="ml-1 text-neutral-300">
                  {idea.rsMomentum.toFixed(1)}
                </span>
              </div>
            </div>

            {/* Thesis */}
            <p className="text-xs text-neutral-400 mb-3 leading-relaxed line-clamp-2">
              {idea.thesis}
            </p>

            {/* Action Button */}
            <button
              onClick={() => handleBacktestClick(idea)}
              className="w-full py-1.5 rounded text-xs font-medium bg-neutral-800 hover:bg-neutral-700 text-neutral-300 hover:text-neutral-100 transition-colors"
            >
              Backtest This
            </button>
          </div>
        ))}
      </div>

      {/* Modal */}
      {selectedIdea && (
        <QuickBacktestModal
          tradeIdea={selectedIdea}
          isOpen={isModalOpen}
          onClose={handleModalClose}
          onSuccess={(backtestId) => {
            console.log('Backtest created:', backtestId);
            // Could redirect to backtest page or show success message
          }}
        />
      )}
    </div>
  );
}
