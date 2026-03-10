import { useLocation, useNavigate } from 'react-router-dom';
import { ModelSelector } from '../settings/ModelSelector';
import { NotificationBell } from '../shared/NotificationBell';
import { NotificationPanel } from '../shared/NotificationPanel';
import { classNames } from '../../lib/utils';
import { useState } from 'react';

const navItems = [
  { label: 'Morning Brief', path: '/' },
  { label: 'Screener', path: '/screener' },
  { label: 'Confluence', path: '/confluence' },
  { label: 'Events', path: '/events' },
  { label: 'Earnings', path: '/earnings' },
  { label: 'Sentiment', path: '/sentiment' },
  { label: 'Weekly Report', path: '/weekly-report' },
  { label: 'Portfolio', path: '/portfolio' },
  { label: 'Correlation', path: '/correlation' },
  { label: 'RRG', path: '/rrg' },
  { label: 'Backtester', path: '/backtester' },
];

export function TopNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const [showNotifications, setShowNotifications] = useState(false);

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
          <div className="ml-2 border-l border-neutral-800 pl-2 flex items-center gap-2">
            <div className="relative">
              <NotificationBell onClick={() => setShowNotifications(!showNotifications)} isOpen={showNotifications} />
              <div className="absolute right-0 top-8 z-50">
                <NotificationPanel isOpen={showNotifications} onClose={() => setShowNotifications(false)} />
              </div>
            </div>
            <ModelSelector />
          </div>
        </div>
      </div>
    </nav>
  );
}
