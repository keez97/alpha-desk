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
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Portfolio Analysis</h1>
        <p className="text-gray-400">Build and optimize your investment portfolios</p>
      </div>

      <div className="grid gap-6">
        {/* Portfolio Creation/Selection */}
        <div className="lg:grid lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1 space-y-4">
            <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-4 max-h-96 overflow-y-auto">
              <h3 className="font-semibold text-white mb-4">Portfolios</h3>
              {portfolios && portfolios.length === 0 ? (
                <p className="text-sm text-gray-500">No portfolios yet</p>
              ) : (
                <div className="space-y-2">
                  {portfolios?.map((portfolio: any) => (
                    <button
                      key={portfolio.id}
                      onClick={() => setSelectedPortfolioId(portfolio.id)}
                      className={`w-full text-left p-3 rounded-lg transition-colors border-l-2 ${
                        selectedPortfolioId === portfolio.id
                          ? 'border-blue-500 bg-gray-700/20'
                          : 'border-transparent hover:bg-gray-700/20'
                      }`}
                    >
                      <p className="font-semibold text-white text-sm">{portfolio.name}</p>
                      <p className="text-xs text-gray-400 mt-1">{formatCurrency(portfolio.capital)}</p>
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

        {/* Analysis */}
        {selectedPortfolio && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">{selectedPortfolio.name} Analysis</h2>
              <button
                onClick={() => deletePortfolio(selectedPortfolioId!)}
                className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/30 transition-colors"
              >
                Delete Portfolio
              </button>
            </div>

            {analysisLoading ? (
              <LoadingState message="Analyzing portfolio..." />
            ) : analysis ? (
              <div className="space-y-6">
                <CorrelationHeatmap analysis={analysis} />
                <OptimisationTable analysis={analysis} />
                <MonteCarloChart analysis={analysis} />
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
