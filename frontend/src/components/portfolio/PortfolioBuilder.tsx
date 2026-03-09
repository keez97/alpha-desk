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
    <form onSubmit={handleSubmit} className="border border-neutral-800 rounded p-4 space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Portfolio"
            className="w-full rounded border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-sm text-neutral-200 placeholder-neutral-600 focus:border-neutral-600 focus:outline-none"
            required
          />
        </div>
        <div>
          <label className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-1">Capital ($)</label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(e.target.value)}
            placeholder="100000"
            step="100"
            min="0"
            className="w-full rounded border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-sm text-neutral-200 placeholder-neutral-600 focus:border-neutral-600 focus:outline-none"
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-1">Add Holdings</label>
        <SearchBar onSelect={handleAddHolding} />
      </div>

      {holdings.length > 0 && (
        <div className="space-y-1.5">
          {holdings.map((holding) => (
            <div key={holding.ticker} className="flex items-center gap-2">
              <span className="font-mono text-xs text-neutral-200 w-14">{holding.ticker}</span>
              <input
                type="number"
                value={holding.shares}
                onChange={(e) => handleUpdateShares(holding.ticker, parseFloat(e.target.value) || 0)}
                placeholder="Shares"
                step="0.01"
                min="0"
                className="flex-1 rounded border border-neutral-800 bg-neutral-950 px-2 py-1 text-xs text-neutral-200 placeholder-neutral-600 focus:border-neutral-600 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => handleRemoveHolding(holding.ticker)}
                className="text-[10px] text-red-400/60 hover:text-red-400 transition-colors px-1"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        type="submit"
        disabled={isPending || !name || !capital || holdings.length === 0}
        className="w-full rounded px-3 py-1.5 text-xs font-medium text-neutral-300 border border-neutral-700 hover:border-neutral-600 hover:text-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        {isPending ? 'Saving...' : portfolio ? 'Update' : 'Create Portfolio'}
      </button>
    </form>
  );
}
