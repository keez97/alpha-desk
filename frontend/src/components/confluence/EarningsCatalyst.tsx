import { useEarningsConfluence, type EarningsCatalyst } from '../../hooks/useEarningsConfluence';

const boostBadgeStyles = {
  HIGH: 'bg-green-500/20 border-green-500/50 text-green-400',
  MEDIUM: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
  NONE: 'bg-gray-500/20 border-gray-500/50 text-gray-400',
};

const boostLabels = {
  HIGH: 'High Impact',
  MEDIUM: 'Medium Impact',
  NONE: 'No Boost',
};

interface EarningsCatalystPanelProps {
  className?: string;
}

function formatEarningsDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

export function EarningsCatalyst({ className = '' }: EarningsCatalystPanelProps) {
  const { data, isLoading, error } = useEarningsConfluence();

  if (isLoading) {
    return (
      <div className={`border border-neutral-800 rounded-lg p-6 bg-neutral-900/50 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg">📅</span>
          <h2 className="text-sm font-semibold text-neutral-100">Earnings Catalysts</h2>
        </div>
        <div className="text-xs text-neutral-500">Loading catalysts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`border border-neutral-800 rounded-lg p-6 bg-neutral-900/50 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg">📅</span>
          <h2 className="text-sm font-semibold text-neutral-100">Earnings Catalysts</h2>
        </div>
        <div className="text-xs text-red-400">Error loading catalysts</div>
      </div>
    );
  }

  const catalysts = data?.catalysts || [];

  // Filter out sectors with no catalysts
  const activeCatalysts = catalysts.filter(c => c.catalystCount > 0);

  if (activeCatalysts.length === 0) {
    return (
      <div className={`border border-neutral-800 rounded-lg p-6 bg-neutral-900/50 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg">📅</span>
          <h2 className="text-sm font-semibold text-neutral-100">Earnings Catalysts</h2>
        </div>
        <div className="text-xs text-neutral-500">No earnings catalysts in next 14 days</div>
      </div>
    );
  }

  return (
    <div className={`border border-neutral-800 rounded-lg p-6 bg-neutral-900/50 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-lg">📅</span>
        <h2 className="text-sm font-semibold text-neutral-100">Earnings Catalysts</h2>
      </div>

      {/* Catalysts List */}
      <div className="space-y-3">
        {activeCatalysts.map((catalyst) => (
          <CatalystCard key={catalyst.sectorTicker} catalyst={catalyst} />
        ))}
      </div>

      {/* Timestamp */}
      <div className="mt-4 pt-3 border-t border-neutral-800">
        <p className="text-xs text-neutral-600">
          Updated: {new Date(data?.timestamp || '').toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

interface CatalystCardProps {
  catalyst: EarningsCatalyst;
}

function CatalystCard({ catalyst }: CatalystCardProps) {
  const boostLevel = catalyst.confluenceBoost;
  const boostStyle = boostBadgeStyles[boostLevel];
  const boostLabel = boostLabels[boostLevel];
  const showConvictionUpgrade =
    boostLevel !== 'NONE' && catalyst.originalConviction !== catalyst.combinedConviction;

  return (
    <div className="border border-neutral-700/50 rounded p-3 bg-neutral-800/30 hover:bg-neutral-800/50 transition-colors">
      {/* Sector Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <h3 className="text-xs font-semibold text-neutral-100">
            {catalyst.sectorTicker}
          </h3>
          <p className="text-xs text-neutral-500 mt-0.5">{catalyst.sectorName}</p>
        </div>
        <div className={`px-2 py-1 rounded text-xs font-semibold border ${boostStyle}`}>
          {boostLabel}
        </div>
      </div>

      {/* Upcoming Earnings */}
      <div className="mb-2">
        <p className="text-xs text-neutral-400 mb-1">
          {catalyst.upcomingEarnings.length} earnings in 14 days:
        </p>
        <div className="flex flex-wrap gap-1">
          {catalyst.upcomingEarnings.map((earning) => (
            <span
              key={earning.ticker}
              className="inline-block px-2 py-0.5 rounded bg-neutral-700/30 text-xs text-neutral-300 border border-neutral-700"
            >
              <span className="font-medium">{earning.ticker}</span>{' '}
              <span className="text-neutral-500">in {earning.daysUntil}d</span>
            </span>
          ))}
        </div>
      </div>

      {/* Conviction Upgrade (if applicable) */}
      {showConvictionUpgrade && (
        <div className="pt-2 border-t border-neutral-700/30">
          <p className="text-xs text-green-400/80">
            Conviction upgraded: {catalyst.originalConviction} → {catalyst.combinedConviction}
          </p>
        </div>
      )}
    </div>
  );
}
