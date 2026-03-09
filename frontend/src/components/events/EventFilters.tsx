import { useState } from 'react';
import { classNames } from '../../lib/utils';
import type { EventFilters as EventFiltersType } from '../../hooks/useEvents';

interface EventFiltersProps {
  onFiltersChange: (filters: EventFiltersType) => void;
}

const EVENT_TYPES = ['8-K', '10-K', '10-Q', 'Earnings', 'FDA', 'Patent', 'Lawsuit', 'Analyst Rating'];
const SEVERITIES = [
  { value: 1, label: 'Minimal' },
  { value: 2, label: 'Low' },
  { value: 3, label: 'Medium' },
  { value: 4, label: 'High' },
  { value: 5, label: 'Critical' },
];

export function EventFilters({ onFiltersChange }: EventFiltersProps) {
  const [ticker, setTicker] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [severityRange, setSeverityRange] = useState<[number, number]>([1, 5]);
  const [dateStart, setDateStart] = useState('');
  const [dateEnd, setDateEnd] = useState('');

  const handleTypeToggle = (type: string) => {
    const updated = selectedTypes.includes(type)
      ? selectedTypes.filter((t) => t !== type)
      : [...selectedTypes, type];
    setSelectedTypes(updated);
    applyFilters({ ticker, selectedTypes: updated, severityRange, dateStart, dateEnd });
  };

  const handleSeverityChange = (min: number, max: number) => {
    setSeverityRange([min, max]);
    applyFilters({ ticker, selectedTypes, severityRange: [min, max], dateStart, dateEnd });
  };

  const applyFilters = (state: any) => {
    const filters: EventFiltersType = {};
    if (state.ticker) filters.ticker = state.ticker;
    if (state.selectedTypes.length > 0) filters.event_type = state.selectedTypes.join(',');
    if (state.severityRange[0] > 1) filters.severity_min = state.severityRange[0];
    if (state.severityRange[1] < 5) filters.severity_max = state.severityRange[1];
    if (state.dateStart) filters.date_start = state.dateStart;
    if (state.dateEnd) filters.date_end = state.dateEnd;
    onFiltersChange(filters);
  };

  const handleTickerChange = (value: string) => {
    setTicker(value);
    applyFilters({ ticker: value, selectedTypes, severityRange, dateStart, dateEnd });
  };

  const handleDateStartChange = (value: string) => {
    setDateStart(value);
    applyFilters({ ticker, selectedTypes, severityRange, dateStart: value, dateEnd });
  };

  const handleDateEndChange = (value: string) => {
    setDateEnd(value);
    applyFilters({ ticker, selectedTypes, severityRange, dateStart, dateEnd: value });
  };

  return (
    <div className="border border-neutral-800 rounded p-3 space-y-3 bg-neutral-950">
      {/* Ticker Search */}
      <div>
        <label className="text-[10px] font-medium text-neutral-400 uppercase">Ticker</label>
        <input
          type="text"
          value={ticker}
          onChange={(e) => handleTickerChange(e.target.value.toUpperCase())}
          placeholder="Search ticker..."
          className="w-full mt-1 px-2 py-1 rounded text-xs bg-neutral-900 border border-neutral-800 text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-neutral-700"
        />
      </div>

      {/* Event Type Checkboxes */}
      <div>
        <label className="text-[10px] font-medium text-neutral-400 uppercase">Event Type</label>
        <div className="grid grid-cols-2 gap-2 mt-2">
          {EVENT_TYPES.map((type) => (
            <label key={type} className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedTypes.includes(type)}
                onChange={() => handleTypeToggle(type)}
                className="w-3 h-3 rounded cursor-pointer"
              />
              <span className="text-xs text-neutral-400">{type}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Severity Range */}
      <div>
        <label className="text-[10px] font-medium text-neutral-400 uppercase">Severity</label>
        <div className="flex gap-2 mt-2 items-center">
          <select
            value={severityRange[0]}
            onChange={(e) => handleSeverityChange(parseInt(e.target.value), severityRange[1])}
            className="flex-1 px-2 py-1 rounded text-xs bg-neutral-900 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-neutral-700"
          >
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}+
              </option>
            ))}
          </select>
          <span className="text-[10px] text-neutral-500">to</span>
          <select
            value={severityRange[1]}
            onChange={(e) => handleSeverityChange(severityRange[0], parseInt(e.target.value))}
            className="flex-1 px-2 py-1 rounded text-xs bg-neutral-900 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-neutral-700"
          >
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Date Range */}
      <div>
        <label className="text-[10px] font-medium text-neutral-400 uppercase">Date Range</label>
        <div className="flex gap-2 mt-2">
          <input
            type="date"
            value={dateStart}
            onChange={(e) => handleDateStartChange(e.target.value)}
            className="flex-1 px-2 py-1 rounded text-xs bg-neutral-900 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-neutral-700"
          />
          <input
            type="date"
            value={dateEnd}
            onChange={(e) => handleDateEndChange(e.target.value)}
            className="flex-1 px-2 py-1 rounded text-xs bg-neutral-900 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-neutral-700"
          />
        </div>
      </div>

      {/* Clear Filters */}
      {(ticker || selectedTypes.length > 0 || severityRange[0] > 1 || severityRange[1] < 5 || dateStart || dateEnd) && (
        <button
          onClick={() => {
            setTicker('');
            setSelectedTypes([]);
            setSeverityRange([1, 5]);
            setDateStart('');
            setDateEnd('');
            onFiltersChange({});
          }}
          className="w-full px-2 py-1 rounded text-xs font-medium text-neutral-400 border border-neutral-800 hover:text-neutral-200 hover:border-neutral-700 transition-colors"
        >
          Clear Filters
        </button>
      )}
    </div>
  );
}
