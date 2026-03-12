import { MacroBar } from '../components/layout/MacroBar';
import { MarketRegimeCard } from '../components/morning-brief/MarketRegimeCard';
import { MarketReportPanel } from '../components/morning-brief/MarketReportPanel';
import { SectorChart } from '../components/morning-brief/SectorChart';
import { SectorTransitionsPanel } from '../components/morning-brief/SectorTransitionsPanel';
import { DriversPanel } from '../components/morning-brief/DriversPanel';
import { MomentumSpilloverPanel } from '../components/morning-brief/MomentumSpilloverPanel';
import { SentimentVelocityPanel } from '../components/morning-brief/SentimentVelocityPanel';
import { OptionsFlowPanel } from '../components/morning-brief/OptionsFlowPanel';
import { EarningsCalendarPanel } from '../components/morning-brief/EarningsCalendarPanel';
import { PositioningPanel } from '../components/morning-brief/PositioningPanel';
import { ScenarioRiskPanel } from '../components/morning-brief/ScenarioRiskPanel';
import { usePrefetchMorningBrief } from '../hooks/usePrefetchMorningBrief';

export function MorningBrief() {
  const { ready, error } = usePrefetchMorningBrief();

  if (!ready) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto" />
          <p className="text-sm text-slate-400">Loading morning brief…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      <MacroBar />

      <div className="p-4 space-y-4">
        {/* Layer 1: Signal - Unified Market Regime Card */}
        <MarketRegimeCard />

        {/* Layer 2: Context - Main Grid */}
        <MarketReportPanel />

        <div className="grid gap-4 lg:grid-cols-3 sm:grid-cols-1">
          <div className="lg:col-span-2 space-y-4">
            <SectorChart />
            <SectorTransitionsPanel />
          </div>

          <div className="space-y-4">
            <DriversPanel />
            <MomentumSpilloverPanel />
          </div>
        </div>

        {/* Layer 3: Detail - Bottom Section */}
        <div className="grid gap-4 lg:grid-cols-2 sm:grid-cols-1">
          <PositioningPanel />
          <ScenarioRiskPanel />
        </div>

        <div className="grid gap-4 lg:grid-cols-3 sm:grid-cols-1">
          <SentimentVelocityPanel />
          <OptionsFlowPanel />
          <EarningsCalendarPanel />
        </div>
      </div>
    </div>
  );
}
