import { Outlet } from 'react-router-dom';
import { TopNav } from './TopNav';

export function AppShell() {
  return (
    <div className="flex flex-col h-screen bg-gray-900">
      <TopNav />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
