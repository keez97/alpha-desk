import { useState } from 'react';
import { useConfluence, useSignalMatrix } from '../hooks/useConfluence';
import { ConfluentThesis } from '../components/confluence/ConfluentThesis';
import { SignalMatrix } from '../components/confluence/SignalMatrix';
import { EarningsCatalyst } from '../components/confluence/EarningsCatalyst';
import { ConfluenceBacktest } from '../components/confluence/ConfluenceBacktest';

export function Confluence() {
  const [activeTab, setActiveTab] = useState<'theses' | 'matrix' | 'earnings' | 'backtest'>('theses');
  const confluenceQuery = useConfluence();
  const matrixQuery = useSignalMatrix();

  const isLoading = confluenceQuery.isLoading || matrixQuery.isLoading;
  const error = confluenceQuery.error || matrixQuery.error;

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="border-b border-neutral-800 pb-4">
        <h1 className="text-2xl font-bold text-neutral-100 mb-2">Signal Confluence</h1>
        <p className="text-sm text-neutral-500">
          Cross-signal synthesis: automatic detection when macro, RRG, and sector performance align
        </p>
      </div>

      {/* Error State */}
      {error && (
        <div className="border border-red-800/50 bg-red-950/20 rounded-lg p-4 text-red-400 text-sm">
          <p className="font-semibold mb-1">Error loading confluence data</p>
          <p className="text-xs text-red-300">{error instanceof Error ? error.message : 'Unknown error'}</p>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-neutral-800">
        <button
          onClick={() => setActiveTab('theses')}
          className={`px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'theses'
              ? 'text-neutral-100 border-b-2 border-amber-500'
              : 'text-neutral-500 hover:text-neutral-400'
          }`}
        >
          Confluent Theses
        </button>
        <button
          onClick={() => setActiveTab('matrix')}
          className={`px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'matrix'
              ? 'text-neutral-100 border-b-2 border-amber-500'
              : 'text-neutral-500 hover:text-neutral-400'
          }`}
        >
          Signal Matrix
        </button>
        <button
          onClick={() => setActiveTab('earnings')}
          className={`px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'earnings'
              ? 'text-neutral-100 border-b-2 border-amber-500'
              : 'text-neutral-500 hover:text-neutral-400'
          }`}
        >
          Earnings Catalysts
        </button>
        <button
          onClick={() => setActiveTab('backtest')}
          className={`px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'backtest'
              ? 'text-neutral-100 border-b-2 border-amber-500'
              : 'text-neutral-500 hover:text-neutral-400'
          }`}
        >
          Backtest
        </button>
      </div>

      {/* Content */}
      <div>
        {activeTab === 'theses' && confluenceQuery.data && (
          <ConfluentThesis data={confluenceQuery.data} isLoading={isLoading} />
        )}
        {activeTab === 'matrix' && matrixQuery.data && (
          <SignalMatrix data={matrixQuery.data} isLoading={isLoading} />
        )}
        {activeTab === 'earnings' && <EarningsCatalyst />}
        {activeTab === 'backtest' && <ConfluenceBacktest />}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="border border-neutral-800 rounded-lg p-8 bg-neutral-900/50 text-center">
          <div className="w-8 h-8 border-2 border-neutral-700 border-t-neutral-400 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-neutral-500">Loading confluence analysis...</p>
        </div>
      )}
    </div>
  );
}
