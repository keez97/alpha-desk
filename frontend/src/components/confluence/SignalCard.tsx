import type { ConfluentSignal } from '../../hooks/useConfluence';

interface SignalCardProps {
  signal: ConfluentSignal;
}

const convictionColors = {
  HIGH: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
  MEDIUM: 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400',
  LOW: 'bg-gray-500/20 border-gray-500/50 text-gray-400',
};

const directionIcons = {
  bullish: '↑',
  bearish: '↓',
  neutral: '→',
};

const directionColors = {
  bullish: 'text-green-400',
  bearish: 'text-red-400',
  neutral: 'text-gray-400',
};

export function SignalCard({ signal }: SignalCardProps) {
  return (
    <div className="border border-neutral-800 rounded-lg p-4 bg-neutral-900/50 hover:bg-neutral-900/80 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-neutral-100">{signal.thesis}</h3>
          <p className="text-xs text-neutral-500 mt-1">{signal.sector}</p>
        </div>
        <div className="flex items-center gap-2 ml-3">
          <span className={`text-2xl font-bold ${directionColors[signal.direction]}`}>
            {directionIcons[signal.direction]}
          </span>
          <div className={`px-2 py-1 rounded text-xs font-semibold border ${convictionColors[signal.conviction]}`}>
            {signal.conviction}
          </div>
        </div>
      </div>

      <div className="space-y-2 mb-3">
        {signal.signals.map((sig, idx) => (
          <div
            key={idx}
            className="flex items-start gap-2 text-xs"
          >
            <span className="text-neutral-600 font-medium min-w-[60px]">{sig.source}</span>
            <span className="text-neutral-400">{sig.detail}</span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-neutral-800">
        <p className="text-xs text-neutral-500">{signal.timeframe}</p>
        <p className="text-xs text-neutral-400 italic">{signal.suggestedAction}</p>
      </div>
    </div>
  );
}
