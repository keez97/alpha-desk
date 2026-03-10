import { useState } from 'react';
import type { QuantFilter, ScreenPreset } from '../../lib/api';

interface FilterBuilderProps {
  presets: ScreenPreset[];
  onApplyFilters: (filters: QuantFilter) => void;
  isLoading?: boolean;
}

const QUADRANTS = ['Strengthening', 'Weakening', 'Recovering', 'Deteriorating'];
const SORT_OPTIONS = [
  { value: 'rs_momentum', label: 'RS-Momentum' },
  { value: 'rs_ratio', label: 'RS-Ratio' },
  { value: 'change_1d', label: '1D Change' },
  { value: 'price', label: 'Price' },
  { value: 'ticker', label: 'Ticker' },
];

export function FilterBuilder({ presets, onApplyFilters, isLoading }: FilterBuilderProps) {
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [filters, setFilters] = useState<QuantFilter>({
    sort_by: 'rs_momentum',
    sort_desc: true,
  });
  const [isExpanded, setIsExpanded] = useState(false);

  const handlePresetClick = (preset: ScreenPreset) => {
    setActivePreset(preset.id);
    const newFilters: QuantFilter = {
      ...preset.filters,
      sort_by: filters.sort_by,
      sort_desc: filters.sort_desc,
    };
    setFilters(newFilters);
    onApplyFilters(newFilters);
  };

  const handleCustomClick = () => {
    setActivePreset(null);
    setIsExpanded(!isExpanded);
  };

  const handleQuadrantChange = (quadrant: string, checked: boolean) => {
    setActivePreset(null);
    const current = filters.rrg_quadrant || [];
    const updated = checked ? [...current, quadrant] : current.filter(q => q !== quadrant);
    const newFilters = {
      ...filters,
      rrg_quadrant: updated.length > 0 ? updated : undefined,
    };
    setFilters(newFilters);
  };

  const handleNumberChange = (key: keyof QuantFilter, value: string) => {
    setActivePreset(null);
    const numValue = value === '' ? undefined : parseFloat(value);
    const newFilters = {
      ...filters,
      [key]: numValue,
    };
    setFilters(newFilters);
  };

  const handleSortChange = (sortBy: string) => {
    const newFilters = {
      ...filters,
      sort_by: sortBy,
    };
    setFilters(newFilters);
  };

  const handleApply = () => {
    onApplyFilters(filters);
  };

  return (
    <div className="space-y-3 bg-neutral-950 border border-neutral-800 rounded p-4">
      {/* Preset buttons */}
      <div className="flex gap-2 flex-wrap items-center">
        {presets.map((preset) => (
          <button
            key={preset.id}
            onClick={() => handlePresetClick(preset)}
            title={preset.description}
            className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              activePreset === preset.id
                ? 'bg-blue-900/50 text-blue-300 border border-blue-700'
                : 'bg-neutral-900 text-neutral-300 border border-neutral-800 hover:border-neutral-700 hover:text-neutral-200'
            }`}
          >
            {preset.name}
          </button>
        ))}

        <button
          onClick={handleCustomClick}
          className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
            activePreset === null && isExpanded
              ? 'bg-purple-900/50 text-purple-300 border border-purple-700'
              : 'bg-neutral-900 text-neutral-300 border border-neutral-800 hover:border-neutral-700 hover:text-neutral-200'
          }`}
        >
          Custom
        </button>
      </div>

      {/* Custom filter controls */}
      {isExpanded && (
        <div className="space-y-3 pt-3 border-t border-neutral-800">
          {/* RRG Quadrant */}
          <div>
            <label className="text-xs font-medium text-neutral-400 block mb-2">
              RRG Quadrant
            </label>
            <div className="flex gap-2 flex-wrap">
              {QUADRANTS.map((q) => (
                <label key={q} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(filters.rrg_quadrant || []).includes(q)}
                    onChange={(e) => handleQuadrantChange(q, e.target.checked)}
                    className="w-3 h-3 rounded border-neutral-700"
                  />
                  <span className="text-xs text-neutral-300">{q}</span>
                </label>
              ))}
            </div>
          </div>

          {/* RS-Momentum Range */}
          <div>
            <label className="text-xs font-medium text-neutral-400 block mb-2">
              RS-Momentum Range
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="number"
                placeholder="Min"
                value={filters.rrg_momentum_min ?? ''}
                onChange={(e) => handleNumberChange('rrg_momentum_min', e.target.value)}
                className="w-20 px-2 py-1 text-xs bg-neutral-900 border border-neutral-800 rounded text-neutral-300 placeholder-neutral-600"
              />
              <span className="text-neutral-500">to</span>
              <input
                type="number"
                placeholder="Max"
                value={filters.rrg_momentum_max ?? ''}
                onChange={(e) => handleNumberChange('rrg_momentum_max', e.target.value)}
                className="w-20 px-2 py-1 text-xs bg-neutral-900 border border-neutral-800 rounded text-neutral-300 placeholder-neutral-600"
              />
            </div>
          </div>

          {/* RS-Ratio Range */}
          <div>
            <label className="text-xs font-medium text-neutral-400 block mb-2">
              RS-Ratio Range
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="number"
                placeholder="Min"
                value={filters.rrg_ratio_min ?? ''}
                onChange={(e) => handleNumberChange('rrg_ratio_min', e.target.value)}
                className="w-20 px-2 py-1 text-xs bg-neutral-900 border border-neutral-800 rounded text-neutral-300 placeholder-neutral-600"
              />
              <span className="text-neutral-500">to</span>
              <input
                type="number"
                placeholder="Max"
                value={filters.rrg_ratio_max ?? ''}
                onChange={(e) => handleNumberChange('rrg_ratio_max', e.target.value)}
                className="w-20 px-2 py-1 text-xs bg-neutral-900 border border-neutral-800 rounded text-neutral-300 placeholder-neutral-600"
              />
            </div>
          </div>

          {/* 1D Change Range */}
          <div>
            <label className="text-xs font-medium text-neutral-400 block mb-2">
              1D Change % Range
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="number"
                placeholder="Min"
                step="0.1"
                value={filters.change_1d_min ?? ''}
                onChange={(e) => handleNumberChange('change_1d_min', e.target.value)}
                className="w-20 px-2 py-1 text-xs bg-neutral-900 border border-neutral-800 rounded text-neutral-300 placeholder-neutral-600"
              />
              <span className="text-neutral-500">to</span>
              <input
                type="number"
                placeholder="Max"
                step="0.1"
                value={filters.change_1d_max ?? ''}
                onChange={(e) => handleNumberChange('change_1d_max', e.target.value)}
                className="w-20 px-2 py-1 text-xs bg-neutral-900 border border-neutral-800 rounded text-neutral-300 placeholder-neutral-600"
              />
            </div>
          </div>

          {/* Sort By */}
          <div>
            <label className="text-xs font-medium text-neutral-400 block mb-2">
              Sort By
            </label>
            <div className="flex gap-2 items-center">
              <select
                value={filters.sort_by || 'rs_momentum'}
                onChange={(e) => handleSortChange(e.target.value)}
                className="flex-1 px-2 py-1 text-xs bg-neutral-900 border border-neutral-800 rounded text-neutral-300"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.sort_desc !== false}
                  onChange={(e) =>
                    setFilters({ ...filters, sort_desc: e.target.checked })
                  }
                  className="w-3 h-3 rounded border-neutral-700"
                />
                <span className="text-xs text-neutral-300">Desc</span>
              </label>
            </div>
          </div>

          {/* Run Button */}
          <button
            onClick={handleApply}
            disabled={isLoading}
            className="w-full px-3 py-2 rounded text-xs font-medium bg-blue-900/50 text-blue-300 border border-blue-700 hover:bg-blue-900/70 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Running...' : 'Run Screen'}
          </button>
        </div>
      )}
    </div>
  );
}
