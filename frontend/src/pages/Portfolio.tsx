import { useState } from 'react';
import { PortfolioBuilder } from '../components/portfolio/PortfolioBuilder';
import { CorrelationHeatmap } from '../components/portfolio/CorrelationHeatmap';
import { OptimisationTable } from '../components/portfolio/OptimisationTable';
import { MonteCarloChart } from '../components/portfolio/MonteCarloChart';
import { usePortfolios, useDeletePortfolio, useAnalyzePortfolio } from '../hooks/usePortfolio';
import { LoadingState } from '../components/shared/LoadingState';
import { ErrorState } from '../components/shared/ErrorState';
import { formatCurrency } from '../lib/utils';

export function Portfolio() {
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(null);
  const { data: portfolios, isLoading, error, refetch } = usePortfolios();
  const { mutate: deletePortfolio } = useDeletePortfolio();
  const { data: analysis, isLoading: analysisLoading } = useAnalyzePortfolio(selectedPortfolioId);

  const selectedPortfolio = portfolios?.find((p) => p.id === selectedPortfolioId);

  if (isLoading) return <LoadingState message="Loading portfolios..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  return (
    <div className="p-4 space-y-4">
      <div className="lg:grid lg:grid-cols-4 gap-4">
        <div className="lg:col-span-1 space-y-3">
          <div className="border border-neutral-800 rounded p-3 max-h-96 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-neutral-300">Portfolios</span>
              <span className="text-[10px] text-neutral-600">{portfolios?.length || 0}</span>
            </div>
            {portfolios && portfolios.length === 0 ? (
              <p className="text-[11px] text-neutral-600">No portfolios yet</p>
            ) : (
              <div className="space-y-1">
                {portfolios?.map((portfolio: any) => (
                  <button
                    key={portfolio.id}
                    onClick={() => setSelectedPortfolioId(portfolio.id)}
                    className={`w-full text-left p-2 rounded transition-colors border-l-2 ${
                      selectedPortfolioId === portfolio.id
                        ? 'border-neutral-400 bg-neutral-900/50'
                        : 'border-transparent hover:bg-neutral-900/30'
                    }`}
                  >
                    <p className="text-xs font-medium text-neutral-200">{portfolio.name}</p>
                    <p className="text-[10px] text-neutral-500 mt-0.5">{formatCurrency(portfolio.capital)}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-3">
          <PortfolioBuilder />
        </div>
      </div>

      {selectedPortfolio && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-300">{selectedPortfolio.name} Analysis</span>
            <button
              onClick={() => deletePortfolio(selectedPortfolioId!)}
              className="px-2 py-1 rounded text-[10px] text-red-400/70 hover:text-red-400 transition-colors"
            >
              Delete
            </button>
          </div>

          {analysisLoading ? (
            <LoadingState message="Analyzing portfolio..." />
          ) : analysis ? (
            <div className="space-y-4">
              <CorrelationHeatmap analysis={analysis} />
              <OptimisationTable analysis={analysis} />
              <MonteCarloChart analysis={analysis} />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
