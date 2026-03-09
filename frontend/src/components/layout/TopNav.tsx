import { useLocation, useNavigate } from 'react-router-dom';
import { classNames } from '../../lib/utils';

const navItems = [
  { label: 'Morning Brief', path: '/' },
  { label: 'Screener', path: '/screener' },
  { label: 'Weekly Report', path: '/weekly-report' },
  { label: 'Portfolio', path: '/portfolio' },
  { label: 'RRG', path: '/rrg' },
];

export function TopNav() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav className="border-b border-gray-700 bg-gray-800/50">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="text-2xl font-bold text-blue-400">AlphaDesk</div>
        <div className="flex space-x-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={classNames(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    : 'text-gray-400 hover:text-gray-300 hover:bg-gray-700/30'
                )}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
