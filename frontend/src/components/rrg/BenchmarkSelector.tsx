import { useState } from 'react';

interface BenchmarkSelectorProps {
  value: string;
  onChange: (benchmark: string) => void;
}

const defaultBenchmarks = ['SPY', 'QQQ', 'IWM', 'DIA'];

export function BenchmarkSelector({ value, onChange }: BenchmarkSelectorProps) {
  const [isCustom, setIsCustom] = useState(!defaultBenchmarks.includes(value));

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-300">Benchmark</label>
      <div className="flex space-x-2">
        <div className="flex-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {defaultBenchmarks.map((bench) => (
            <button
              key={bench}
              onClick={() => {
                onChange(bench);
                setIsCustom(false);
              }}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                value === bench && !isCustom
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'bg-gray-700/30 text-gray-400 hover:bg-gray-700/50 border border-gray-700'
              }`}
            >
              {bench}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <input
          type="checkbox"
          id="custom"
          checked={isCustom}
          onChange={(e) => {
            setIsCustom(e.target.checked);
            if (!e.target.checked && defaultBenchmarks.includes(value)) {
              onChange('SPY');
            }
          }}
          className="rounded cursor-pointer"
        />
        <label htmlFor="custom" className="text-sm text-gray-400 cursor-pointer">
          Custom
        </label>
      </div>

      {isCustom && (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value.toUpperCase())}
          placeholder="Enter ticker..."
          className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      )}
    </div>
  );
}
