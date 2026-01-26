/**
 * Main Layout Component
 *
 * Provides the application shell with sidebar navigation and main content area.
 * Responsive design with collapsible sidebar for mobile.
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Trophy,
  Users,
  UserCircle,
  Gamepad2,
  RefreshCw,
  Home,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: Home, label: 'Dashboard' },
  { to: '/leagues', icon: Trophy, label: 'Leagues' },
  { to: '/teams', icon: Users, label: 'Teams' },
  { to: '/players', icon: UserCircle, label: 'Players' },
  { to: '/games', icon: Gamepad2, label: 'Games' },
  { to: '/sync', icon: RefreshCw, label: 'Sync' },
];

function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const location = useLocation();

  // Close sidebar on route change (mobile)
  useEffect(() => {
    onClose();
  }, [location.pathname, onClose]);

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 bg-white border-r border-gray-200 flex flex-col
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Logo/Brand */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
          <Link to="/" className="flex items-center gap-2" onClick={onClose}>
            <span className="text-2xl">🏀</span>
            <span className="font-bold text-lg text-gray-900">Basketball</span>
          </Link>
          {/* Close button for mobile */}
          <button
            onClick={onClose}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors ${
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
            Basketball Analytics
          </p>
        </div>
      </aside>
    </>
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
        <ChevronRight className="w-4 h-4 mx-1 sm:mx-2 text-gray-400" />
        {isLast ? (
          <span className="text-gray-900 font-medium truncate max-w-[100px] sm:max-w-none">{label}</span>
        ) : (
          <Link to={path} className="text-gray-500 hover:text-gray-700 truncate max-w-[80px] sm:max-w-none">
            {label}
          </Link>
        )}
      </span>
    );
  });

  return (
    <div className="flex items-center text-sm overflow-x-auto">
      <Link to="/" className="text-gray-500 hover:text-gray-700 flex-shrink-0">
        Home
      </Link>
      {breadcrumbs}
    </div>
  );
}

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const handleCloseSidebar = useCallback(() => setSidebarOpen(false), []);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar isOpen={sidebarOpen} onClose={handleCloseSidebar} />

      <div className="flex-1 flex flex-col overflow-hidden w-full">
        {/* Header */}
        <header className="h-14 sm:h-16 bg-white border-b border-gray-200 flex items-center px-3 sm:px-6 gap-3">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 -ml-1 rounded-lg hover:bg-gray-100"
          >
            <Menu className="w-6 h-6 text-gray-600" />
          </button>

          {/* Mobile logo */}
          <Link to="/" className="lg:hidden flex items-center gap-2">
            <span className="text-xl">🏀</span>
          </Link>

          {/* Breadcrumbs - hidden on small mobile */}
          <div className="hidden sm:block flex-1">
            <Breadcrumbs />
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto p-3 sm:p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
