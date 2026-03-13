/**
 * DashboardToolbar — controls for customizing the dashboard layout.
 * Add widgets, lock/unlock, reset to default.
 */
import { useState, useRef, useEffect } from 'react';
import { useDashboardStore } from '../../lib/dashboardStore';
import { WIDGET_REGISTRY, WIDGET_CATEGORIES } from '../../lib/widgetRegistry';

export function DashboardToolbar() {
  const { visibleWidgets, isLocked, addWidget, toggleLock, resetToDefault } = useDashboardStore();
  const [showPicker, setShowPicker] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  // Close picker on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowPicker(false);
      }
    }
    if (showPicker) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showPicker]);

  const allWidgets = Object.values(WIDGET_REGISTRY);
  const hiddenWidgets = allWidgets.filter(w => !visibleWidgets.includes(w.id));
  const filteredHidden = activeCategory === 'all'
    ? hiddenWidgets
    : hiddenWidgets.filter(w => w.category === activeCategory);

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-neutral-900/80 border-b border-neutral-800">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-neutral-200">Morning Brief</h1>
        <span className="text-xs text-neutral-500">
          {visibleWidgets.length} / {allWidgets.length} widgets
        </span>
      </div>

      <div className="flex items-center gap-2">
        {/* Add Widget */}
        <div className="relative" ref={pickerRef}>
          <button
            onClick={() => setShowPicker(!showPicker)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-neutral-300 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded transition-colors"
            aria-label="Add widget"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="8" y1="3" x2="8" y2="13" />
              <line x1="3" y1="8" x2="13" y2="8" />
            </svg>
            Add Widget
          </button>

          {showPicker && (
            <div className="absolute right-0 top-full mt-1 w-80 bg-neutral-850 bg-neutral-900 border border-neutral-700 rounded-lg shadow-xl z-50 overflow-hidden">
              {/* Category tabs */}
              <div className="flex gap-1 px-2 pt-2 pb-1 border-b border-neutral-800 overflow-x-auto">
                <button
                  onClick={() => setActiveCategory('all')}
                  className={`px-2 py-1 text-xs rounded whitespace-nowrap ${
                    activeCategory === 'all'
                      ? 'bg-blue-600/20 text-blue-400'
                      : 'text-neutral-400 hover:text-neutral-300'
                  }`}
                >
                  All
                </button>
                {WIDGET_CATEGORIES.map(cat => (
                  <button
                    key={cat.key}
                    onClick={() => setActiveCategory(cat.key)}
                    className={`px-2 py-1 text-xs rounded whitespace-nowrap ${
                      activeCategory === cat.key
                        ? 'bg-blue-600/20 text-blue-400'
                        : 'text-neutral-400 hover:text-neutral-300'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              {/* Widget list */}
              <div className="max-h-64 overflow-y-auto p-2 space-y-1">
                {filteredHidden.length === 0 ? (
                  <div className="text-center py-4 text-xs text-neutral-500">
                    {hiddenWidgets.length === 0
                      ? 'All widgets are visible'
                      : 'No hidden widgets in this category'}
                  </div>
                ) : (
                  filteredHidden.map(widget => (
                    <button
                      key={widget.id}
                      onClick={() => {
                        addWidget(widget.id);
                        if (hiddenWidgets.length <= 1) setShowPicker(false);
                      }}
                      className="w-full flex items-start gap-3 px-3 py-2 rounded hover:bg-neutral-800 transition-colors text-left"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-neutral-200">{widget.name}</div>
                        <div className="text-xs text-neutral-500 mt-0.5 line-clamp-1">{widget.description}</div>
                      </div>
                      <svg className="w-4 h-4 text-neutral-500 shrink-0 mt-0.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="8" y1="3" x2="8" y2="13" />
                        <line x1="3" y1="8" x2="13" y2="8" />
                      </svg>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Lock/Unlock */}
        <button
          onClick={toggleLock}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium border rounded transition-colors ${
            isLocked
              ? 'text-neutral-400 bg-neutral-800 border-neutral-700 hover:bg-neutral-700'
              : 'text-blue-400 bg-blue-900/20 border-blue-700/50 hover:bg-blue-900/30'
          }`}
          title={isLocked ? 'Unlock to edit layout' : 'Lock layout'}
          aria-label={isLocked ? 'Unlock dashboard layout' : 'Lock dashboard layout'}
        >
          {isLocked ? (
            <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
              <path d="M11 6V4.5a3 3 0 10-6 0V6H4a1 1 0 00-1 1v6a1 1 0 001 1h8a1 1 0 001-1V7a1 1 0 00-1-1h-1zm-4.5-1.5a1.5 1.5 0 113 0V6h-3V4.5z"/>
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
              <path d="M11 6h1a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1V7a1 1 0 011-1h5V4.5a1.5 1.5 0 113 0v.5h-1.5v-.5a.01.01 0 00-.01-.01H10a.01.01 0 00-.01.01V6z"/>
            </svg>
          )}
          {isLocked ? 'Locked' : 'Editing'}
        </button>

        {/* Reset */}
        <div className="relative">
          {showResetConfirm ? (
            <div className="flex items-center gap-1">
              <span className="text-xs text-neutral-400">Reset?</span>
              <button
                onClick={() => {
                  resetToDefault();
                  setShowResetConfirm(false);
                }}
                className="px-2 py-1 text-xs text-red-400 bg-red-900/20 border border-red-700/50 rounded hover:bg-red-900/30"
              >
                Yes
              </button>
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-2 py-1 text-xs text-neutral-400 bg-neutral-800 border border-neutral-700 rounded hover:bg-neutral-700"
              >
                No
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowResetConfirm(true)}
              className="px-2.5 py-1.5 text-xs font-medium text-neutral-500 hover:text-neutral-300 border border-neutral-700 rounded transition-colors"
              title="Reset to default layout"
              aria-label="Reset dashboard to default layout"
            >
              Reset
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
