import { useState } from 'react';
import { SearchBar } from '../screener/SearchBar';
import { useCreatePortfolio, useUpdatePortfolio } from '../../hooks/usePortfolio';
import type { Portfolio } from '../../lib/api';

interface PortfolioBuilderProps {
  portfolio?: Portfolio;
  onSuccess?: () => void;
}

interface Holding {
  ticker: string;
  shares: number;
}

export function PortfolioBuilder({ portfolio, onSuccess }: PortfolioBuilderProps) {
  const [name, setName] = useState(portfolio?.name || '');
  const [capital, setCapital] = useState(portfolio?.capital.toString() || '');
  const [holdings, setHoldings] = useState<Holding[]>(portfolio?.holdings || []);

  const { mutate: create, isPending: isCreating } = useCreatePortfolio();
  const { mutate: update, isPending: isUpdating } = useUpdatePortfolio();

  const handleAddHolding = (ticker: string) => {
    if (!holdings.find((h) => h.ticker === ticker)) {
      setHoldings([...holdings, { ticker, shares: 0 }]);
    }
  };

  const handleRemoveHolding = (ticker: string) => {
    setHoldings(holdings.filter((h) => h.ticker !== ticker));
  };

  const handleUpdateShares = (ticker: string, shares: number) => {
    setHoldings(holdings.map((h) => (h.ticker === ticker ? { ...h, shares } : h)));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const data = {
      name,
      capital: parseFloat(capital),
      holdings,
    };

    if (portfolio) {
      update({ id: portfolio.id, data });
    } else {
      create(data);
    }

    if (onSuccess) onSuccess();
  };

  const isPending = isCreating || isUpdating;

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-gray-700 bg-gray-800/30 p-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Portfolio Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Growth Portfolio"
          className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Initial Capital ($)</label>
        <input
          type="number"
          value={capital}
          onChange={(e) => setCapital(e.target.value)}
          placeholder="100000"
          step="100"
          min="0"
          className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Add Holdings</label>
        <SearchBar onSelect={handleAddHolding} />
      </div>

      {holdings.length > 0 && (
        <div className="rounded-lg bg-gray-700/20 p-4">
          <h3 className="font-semibold text-white mb-3">Holdings</h3>
          <div className="space-y-2">
            {holdings.map((holding) => (
              <div key={holding.ticker} className="flex items-center justify-between">
                <div className="flex-1">
                  <input
                    type="number"
                    value={holding.shares}
                    onChange={(e) => handleUpdateShares(holding.ticker, parseFloat(e.target.value) || 0)}
                    placeholder="Shares"
                    step="0.01"
                    min="0"
                    className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-2 text-white text-sm placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <span className="mx-3 font-mono text-white font-semibold">{holding.ticker}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveHolding(holding.ticker)}
                  className="px-3 py-2 rounded-lg bg-red-500/20 text-red-400 text-sm hover:bg-red-500/30 transition-colors"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isPending || !name || !capital || holdings.length === 0}
        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isPending ? 'Saving...' : portfolio ? 'Update Portfolio' : 'Create Portfolio'}
      </button>
    </form>
  );
}
