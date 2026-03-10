import type { BacktestResult } from '../../lib/api';

interface AlphaDecayPanelProps {
  results: BacktestResult;
}

export function AlphaDecayPanel({ results }: AlphaDecayPanelProps) {
  const alphaDec = results.alpha_decay;

  if (!alphaDec) {
    return (
      <div className="border border-neutral-800 rounded p-4 bg-black">
        <p className="text-xs text-neutral-500">No alpha decay data available</p>
      </div>
    );
  }

  const preReturn = alphaDec.pre_publication_return * 100;
  const postReturn = alphaDec.post_publication_return * 100;
  const decay = alphaDec.decay_percent;

  const decayColor = decay > 30 ? 'text-red-400' : decay > 15 ? 'text-yellow-400' : 'text-green-400';

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-4 bg-black">
      <div>
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">Alpha Decay Analysis</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="border border-neutral-800 rounded p-3 bg-neutral-900/20">
          <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Pre-Publication Return</p>
          <p className="text-sm font-mono text-green-400/70 mt-1">{preReturn.toFixed(2)}%</p>
        </div>
        <div className="border border-neutral-800 rounded p-3 bg-neutral-900/20">
          <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Post-Publication Return</p>
          <p className="text-sm font-mono text-green-400/70 mt-1">{postReturn.toFixed(2)}%</p>
        </div>
      </div>

      <div className="border border-neutral-800 rounded p-3 bg-neutral-900/20">
        <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Decay Percentage</p>
        <p className={`text-sm font-mono mt-1 ${decayColor}`}>{decay.toFixed(2)}%</p>
        {decay > 30 && (
          <p className="text-[10px] text-red-400 mt-2">
            High decay may indicate factor saturation or increased competition.
          </p>
        )}
      </div>

      <p className="text-[10px] text-neutral-600 border-t border-neutral-800 pt-3">
        Alpha decay measures the performance degradation between the factor's pre-publication period and post-publication period,
        indicating how quickly alpha dissipates as more investors adopt the strategy.
      </p>
    </div>
  );
}
