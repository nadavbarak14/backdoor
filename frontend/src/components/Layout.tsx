/**
 * Main Layout Component
 *
 * Provides the application shell with sidebar navigation and main content area.
 */

import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Trophy,
  Users,
  UserCircle,
  Gamepad2,
  RefreshCw,
  Home,
  ChevronRight,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: Home, label: 'Dashboard' },
  { to: '/leagues', icon: Trophy, label: 'Leagues' },
  { to: '/teams', icon: Users, label: 'Teams' },
  { to: '/players', icon: UserCircle, label: 'Players' },
  { to: '/games', icon: Gamepad2, label: 'Games' },
  { to: '/sync', icon: RefreshCw, label: 'Sync' },
];

function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo/Brand */}
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <Link to="/" className="flex items-center gap-2">
          <span className="text-2xl">🏀</span>
          <span className="font-bold text-lg text-gray-900">Basketball Analytics</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <Icon className="w-5 h-5" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Basketball Analytics Platform
        </p>
      </div>
    </aside>
  );
}

function Breadcrumbs() {
  const location = useLocation();
  const pathParts = location.pathname.split('/').filter(Boolean);

  if (pathParts.length === 0) return null;

  const breadcrumbs = pathParts.map((part, index) => {
    const path = '/' + pathParts.slice(0, index + 1).join('/');
    const isLast = index === pathParts.length - 1;
    // Capitalize first letter and handle IDs
    const label = part.length === 36 ? 'Details' : part.charAt(0).toUpperCase() + part.slice(1);

    return (
      <span key={path} className="flex items-center">
        <ChevronRight className="w-4 h-4 mx-2 text-gray-400" />
        {isLast ? (
          <span className="text-gray-900 font-medium">{label}</span>
        ) : (
          <Link to={path} className="text-gray-500 hover:text-gray-700">
            {label}
          </Link>
        )}
      </span>
    );
  });

  return (
    <div className="flex items-center text-sm">
      <Link to="/" className="text-gray-500 hover:text-gray-700">
        Home
      </Link>
      {breadcrumbs}
    </div>
  );
}

export function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
          <Breadcrumbs />
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
