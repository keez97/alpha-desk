import { MacroBar } from '../components/layout/MacroBar';
import { EnhancedSectorPanel } from '../components/morning-brief/EnhancedSectorPanel';
import { SectorChart } from '../components/morning-brief/SectorChart';
import { DriversPanel } from '../components/morning-brief/DriversPanel';
import { MarketReportPanel } from '../components/morning-brief/MarketReportPanel';

export function MorningBrief() {
  return (
    <div className="space-y-0">
      <MacroBar />

      <div className="p-4 space-y-4">
        <MarketReportPanel />

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            <EnhancedSectorPanel />
            <SectorChart />
          </div>

          <div>
            <DriversPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
