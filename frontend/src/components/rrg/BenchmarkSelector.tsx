import { useState } from 'react';

interface BenchmarkSelectorProps {
  value: string;
  onChange: (benchmark: string) => void;
}

const defaultBenchmarks = ['SPY', 'QQQ', 'IWM', 'DIA'];

export function BenchmarkSelector({ value, onChange }: BenchmarkSelectorProps) {
  const [isCustom, setIsCustom] = useState(!defaultBenchmarks.includes(value));

  return (
    <div className="space-y-2">
      <span className="block text-[10px] text-neutral-500 uppercase tracking-wider">Benchmark</span>
      <div className="grid grid-cols-2 gap-1">
        {defaultBenchmarks.map((bench) => (
          <button
            key={bench}
            onClick={() => {
              onChange(bench);
              setIsCustom(false);
            }}
            className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
              value === bench && !isCustom
                ? 'bg-neutral-800 text-neutral-200'
                : 'text-neutral-500 hover:text-neutral-300'
            }`}
          >
            {bench}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-1.5">
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
          className="rounded cursor-pointer w-3 h-3"
        />
        <label htmlFor="custom" className="text-[11px] text-neutral-500 cursor-pointer">
          Custom
        </label>
      </div>

      {isCustom && (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value.toUpperCase())}
          placeholder="Ticker..."
          className="w-full rounded border border-neutral-800 bg-neutral-950 px-2 py-1 text-xs text-neutral-200 placeholder-neutral-600 focus:border-neutral-600 focus:outline-none"
        />
      )}
    </div>
  );
}
