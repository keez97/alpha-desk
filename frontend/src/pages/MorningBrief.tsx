import { MacroBar } from '../components/layout/MacroBar';
import { SectorPanel } from '../components/morning-brief/SectorPanel';
import { SectorChart } from '../components/morning-brief/SectorChart';
import { DriversPanel } from '../components/morning-brief/DriversPanel';
import { MarketReportPanel } from '../components/morning-brief/MarketReportPanel';

export function MorningBrief() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Morning Brief</h1>
        <p className="text-gray-400">Daily market overview and key drivers</p>
      </div>

      <MacroBar />

      {/* Auto-generated Morning Report */}
      <MarketReportPanel />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <SectorPanel />
          <SectorChart />
        </div>

        <div>
          <DriversPanel />
        </div>
      </div>
    </div>
  );
}
