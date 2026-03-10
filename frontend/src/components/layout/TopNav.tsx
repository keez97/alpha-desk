import { useLocation, useNavigate } from 'react-router-dom';
import { ModelSelector } from '../settings/ModelSelector';
import { classNames } from '../../lib/utils';

const navItems = [
  { label: 'Morning Brief', path: '/' },
  { label: 'Screener', path: '/screener' },
  { label: 'Events', path: '/events' },
  { label: 'Earnings', path: '/earnings' },
  { label: 'Sentiment', path: '/sentiment' },
  { label: 'Weekly Report', path: '/weekly-report' },
  { label: 'Portfolio', path: '/portfolio' },
  { label: 'RRG', path: '/rrg' },
  { label: 'Backtester', path: '/backtester' },
];

export function TopNav() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav className="border-b border-neutral-800 bg-black">
      <div className="flex items-center justify-between px-4 h-10">
        <div className="text-sm font-semibold tracking-wide text-neutral-400 uppercase">AlphaDesk</div>
        <div className="flex items-center gap-1">
          <div className="flex gap-0.5">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={classNames(
                  'px-3 py-1 rounded text-xs font-medium transition-colors',
                  isActive
                    ? 'bg-neutral-800 text-white'
                    : 'text-neutral-500 hover:text-neutral-300 hover:bg-neutral-900'
                )}
              >
                {item.label}
              </button>
            );
          })}
          </div>
          <div className="ml-2 border-l border-neutral-800 pl-2">
            <ModelSelector />
          </div>
        </div>
      </div>
    </nav>
  );
}
