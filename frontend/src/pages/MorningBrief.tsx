import { MacroBar } from '../components/layout/MacroBar';
import { DashboardGrid } from '../components/dashboard/DashboardGrid';
import { DashboardToolbar } from '../components/dashboard/DashboardToolbar';
import { usePrefetchMorningBrief } from '../hooks/usePrefetchMorningBrief';

export function MorningBrief() {
  const { ready } = usePrefetchMorningBrief();

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
    <div className="min-h-screen">
      <MacroBar />
      <DashboardToolbar />
      <DashboardGrid />
    </div>
  );
}
