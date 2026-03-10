import { useState, useEffect } from 'react';
import { useFactors, useCreateBacktest, useRunBacktest } from '../../hooks/useBacktester';
import type { CreateBacktestRequest, Factor } from '../../lib/api';
import { LoadingState } from '../shared/LoadingState';

interface BacktestConfigProps {
  onSubmit: (backtest: any) => void;
  isRunning?: boolean;
}

export function BacktestConfig({ onSubmit, isRunning = false }: BacktestConfigProps) {
  const { data: factorsData, isLoading: factorsLoading } = useFactors();
  const { mutate: createBacktest, isPending: isCreating } = useCreateBacktest();
  const { mutate: runBacktest } = useRunBacktest();

  // Form state
  const [name, setName] = useState('Backtest 1');
  const [startDate, setStartDate] = useState('2020-01-01');
  const [endDate, setEndDate] = useState('2024-01-01');
  const [rebalanceFrequency, setRebalanceFrequency] = useState<'Monthly' | 'Quarterly' | 'Annual'>('Monthly');
  const [universe, setUniverse] = useState('S&P 500');
  const [commissionBps, setCommissionBps] = useState(10);
  const [slippageBps, setSlippageBps] = useState(5);

  // Factor selection
  const [selectedFactors, setSelectedFactors] = useState<Set<number>>(new Set([1, 2, 3, 4, 5]));
  const [weights, setWeights] = useState<Record<number, number>>({
    1: 20,
    2: 20,
    3: 20,
    4: 20,
    5: 20,
  });
  const [useEqualWeight, setUseEqualWeight] = useState(true);

  const factors = factorsData?.factors || [];

  // Update weights when equal weight is toggled
  useEffect(() => {
    if (useEqualWeight && selectedFactors.size > 0) {
      const eqWeight = 100 / selectedFactors.size;
      const newWeights: Record<number, number> = {};
      selectedFactors.forEach((id) => {
        newWeights[id] = parseFloat(eqWeight.toFixed(2));
      });
      setWeights(newWeights);
    }
  }, [useEqualWeight, selectedFactors]);

  // Handle factor selection toggle
  const handleFactorToggle = (factorId: number) => {
    const newSelected = new Set(selectedFactors);
    if (newSelected.has(factorId)) {
      newSelected.delete(factorId);
    } else {
      newSelected.add(factorId);
    }
    setSelectedFactors(newSelected);

    // Initialize weight for new factor
    if (!newSelected.has(factorId)) {
      const newWeights = { ...weights };
      delete newWeights[factorId];
      setWeights(newWeights);
    } else {
      setWeights({ ...weights, [factorId]: 0 });
    }
  };

  // Handle weight change
  const handleWeightChange = (factorId: number, value: number) => {
    const newWeights = { ...weights, [factorId]: value };
    setWeights(newWeights);
    setUseEqualWeight(false); // Disable equal weight when manually adjusting
  };

  // Calculate remaining weight
  const totalWeight = Array.from(selectedFactors).reduce((sum, id) => sum + (weights[id] || 0), 0);
  const remainingWeight = 100 - totalWeight;

  // Handle run backtest
  const handleRun = () => {
    if (selectedFactors.size === 0) {
      alert('Please select at least one factor');
      return;
    }

    if (Math.abs(remainingWeight) > 0.01) {
      alert(`Weights must sum to 100%. Currently: ${totalWeight.toFixed(2)}%`);
      return;
    }

    const factorAllocations: Record<string, number> = {};
    Array.from(selectedFactors).forEach((id) => {
      const factor = factors.find((f: Factor) => f.id === id);
      if (factor) {
        factorAllocations[factor.name] = weights[id] || 0;
      }
    });

    const backtest: CreateBacktestRequest = {
      name,
      start_date: startDate,
      end_date: endDate,
      rebalance_frequency: rebalanceFrequency,
      transaction_costs: {
        commission_bps: commissionBps,
        slippage_bps: slippageBps,
      },
      universe_selection: universe,
      factor_allocations: factorAllocations,
    };

    createBacktest(backtest, {
      onSuccess: (result) => {
        if (result.id) {
          onSubmit(result);
          runBacktest(result.id);
        }
      },
    });
  };

  if (factorsLoading) {
    return <LoadingState message="Loading factors..." />;
  }

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-4 bg-black">
      <div>
        <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isRunning}
          className="w-full mt-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 placeholder-neutral-600 disabled:opacity-50"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={isRunning}
            className="w-full mt-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 disabled:opacity-50"
          />
        </div>
        <div>
          <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={isRunning}
            className="w-full mt-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 disabled:opacity-50"
          />
        </div>
      </div>

      <div>
        <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Rebalance Frequency</label>
        <select
          value={rebalanceFrequency}
          onChange={(e) => setRebalanceFrequency(e.target.value as any)}
          disabled={isRunning}
          className="w-full mt-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 disabled:opacity-50"
        >
          <option>Monthly</option>
          <option>Quarterly</option>
          <option>Annual</option>
        </select>
      </div>

      <div>
        <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Universe</label>
        <select
          value={universe}
          onChange={(e) => setUniverse(e.target.value)}
          disabled={isRunning}
          className="w-full mt-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 disabled:opacity-50"
        >
          <option>S&P 500</option>
          <option>NASDAQ 100</option>
          <option>Russell 2000</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Commission (bps)</label>
          <input
            type="number"
            value={commissionBps}
            onChange={(e) => setCommissionBps(Number(e.target.value))}
            disabled={isRunning}
            className="w-full mt-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 disabled:opacity-50"
          />
        </div>
        <div>
          <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Slippage (bps)</label>
          <input
            type="number"
            value={slippageBps}
            onChange={(e) => setSlippageBps(Number(e.target.value))}
            disabled={isRunning}
            className="w-full mt-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 disabled:opacity-50"
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Factors</label>
          <button
            onClick={() => setUseEqualWeight(!useEqualWeight)}
            disabled={isRunning}
            className="text-[10px] px-2 py-1 rounded border border-neutral-800 text-neutral-400 hover:text-neutral-200 hover:border-neutral-700 disabled:opacity-50"
          >
            {useEqualWeight ? 'Equal Weight' : 'Custom Weight'}
          </button>
        </div>
        <div className="space-y-2">
          {factors.map((factor: Factor) => (
            <div key={factor.id} className="space-y-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedFactors.has(factor.id)}
                  onChange={() => handleFactorToggle(factor.id)}
                  disabled={isRunning}
                  className="w-3 h-3 rounded border-neutral-700 text-neutral-400 disabled:opacity-50"
                />
                <span className="text-xs text-neutral-300">{factor.name}</span>
              </label>
              {selectedFactors.has(factor.id) && (
                <div className="ml-5 flex items-center gap-2">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="0.1"
                    value={weights[factor.id] || 0}
                    onChange={(e) => handleWeightChange(factor.id, Number(e.target.value))}
                    disabled={isRunning || useEqualWeight}
                    className="flex-1 disabled:opacity-50"
                  />
                  <span className="text-[10px] text-neutral-500 w-12 text-right">
                    {(weights[factor.id] || 0).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-2 text-[10px] text-neutral-500">
          Remaining: <span className={remainingWeight > 0.01 || remainingWeight < -0.01 ? 'text-red-400' : 'text-green-400'}>
            {remainingWeight.toFixed(2)}%
          </span>
        </div>
      </div>

      <button
        onClick={handleRun}
        disabled={isRunning || isCreating || selectedFactors.size === 0}
        className="w-full py-2 rounded text-xs font-medium uppercase tracking-wider border border-neutral-800 text-neutral-400 hover:text-neutral-200 hover:border-neutral-700 disabled:opacity-50 transition-colors"
      >
        {isRunning || isCreating ? 'Running...' : 'Run Backtest'}
      </button>
    </div>
  );
}
