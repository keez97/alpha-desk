/**
 * WidgetWrapper — visual wrapper for each grid widget.
 * Provides drag handle, remove button (when unlocked), and overflow handling.
 */
import type { ReactNode } from 'react';

interface WidgetWrapperProps {
  widgetId: string;
  name: string;
  isLocked: boolean;
  onRemove: () => void;
  children: ReactNode;
}

export function WidgetWrapper({ name, isLocked, onRemove, children }: WidgetWrapperProps) {
  return (
    <div className="h-full flex flex-col bg-neutral-900 border border-neutral-800 rounded-lg overflow-hidden">
      {/* Header bar — only shows drag handle + remove when unlocked */}
      {!isLocked && (
        <div className="widget-drag-handle flex items-center justify-between px-3 py-1.5 bg-neutral-800/60 border-b border-neutral-700/50 cursor-grab active:cursor-grabbing select-none shrink-0">
          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-neutral-500" viewBox="0 0 16 16" fill="currentColor">
              <circle cx="4" cy="3" r="1.5" />
              <circle cx="12" cy="3" r="1.5" />
              <circle cx="4" cy="8" r="1.5" />
              <circle cx="12" cy="8" r="1.5" />
              <circle cx="4" cy="13" r="1.5" />
              <circle cx="12" cy="13" r="1.5" />
            </svg>
            <span className="text-xs text-neutral-400 font-medium">{name}</span>
          </div>
          <button
            onClick={onRemove}
            className="text-neutral-500 hover:text-red-400 transition-colors p-0.5 rounded"
            title={`Remove ${name}`}
            aria-label={`Remove ${name} widget`}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="4" y1="4" x2="12" y2="12" />
              <line x1="12" y1="4" x2="4" y2="12" />
            </svg>
          </button>
        </div>
      )}
      {/* Widget content — overflow-auto for scrollable panels */}
      <div className="flex-1 overflow-auto min-h-0">
        {children}
      </div>
    </div>
  );
}
