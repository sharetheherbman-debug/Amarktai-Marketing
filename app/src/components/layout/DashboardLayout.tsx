import { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home,
  PenTool,
  Calendar,
  BarChart2,
  Plug,
  Settings,
  Menu,
  X,
  Bell,
  ChevronDown,
  LogOut,
  User,
  Building2,
  Plus,
} from 'lucide-react';

import { useAuth } from '@/lib/auth';
import { useWebapp } from '@/hooks/useWebapp';
import ThemeToggle from '@/components/ui/ThemeToggle';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: Home },
  { label: 'Businesses', href: '/dashboard/businesses', icon: Building2 },
  { label: 'Content Studio', href: '/dashboard/content', icon: PenTool },
  { label: 'Calendar / Scheduler', href: '/dashboard/scheduler', icon: Calendar },
  { label: 'Analytics', href: '/dashboard/analytics', icon: BarChart2 },
  { label: 'Integrations', href: '/dashboard/integrations', icon: Plug },
  { label: 'Settings', href: '/dashboard/settings', icon: Settings },
];

const PAGE_TITLES: Record<string, string> = {
  dashboard: 'Dashboard',
  businesses: 'Businesses',
  content: 'Content Studio',
  scheduler: 'Calendar / Scheduler',
  analytics: 'Analytics',
  integrations: 'Integrations',
  settings: 'Settings',
};

function NavLink({ item, pathname, onClick }: { item: NavItem; pathname: string; onClick?: () => void }) {
  const Icon = item.icon;
  const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

  return (
    <Link
      to={item.href}
      onClick={onClick}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
        isActive
          ? 'border border-blue-500/30 bg-blue-500/15 text-blue-300'
          : 'text-slate-300 hover:bg-white/5 hover:text-white'
      }`}
    >
      <Icon className="h-4 w-4" />
      <span>{item.label}</span>
    </Link>
  );
}

function Sidebar({
  pathname,
  userLabel,
  isOpen,
  onClose,
}: {
  pathname: string;
  userLabel: string;
  isOpen?: boolean;
  onClose?: () => void;
}) {
  return (
    <aside className="flex h-full w-72 flex-col border-r border-[#1E2130] bg-[#0D0F14]">
      <div className="flex h-16 items-center justify-between border-b border-[#1E2130] px-4">
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Building2 className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">AmarktAI Marketing</p>
            <p className="text-xs text-slate-400">Beta command center</p>
          </div>
        </Link>
        {isOpen ? (
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-white/5 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      <div className="border-b border-[#1E2130] p-4">
        <Link
          to="/dashboard/businesses/new"
          onClick={onClose}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" />
          Add Business
        </Link>
      </div>

      <nav className="flex-1 space-y-2 overflow-y-auto p-4">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.href} item={item} pathname={pathname} onClick={onClose} />
        ))}
      </nav>

      <div className="border-t border-[#1E2130] p-4">
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <p className="truncate text-sm font-medium text-white">{userLabel}</p>
          <p className="mt-1 text-xs text-slate-400">Beta flow repair mode</p>
        </div>
      </div>
    </aside>
  );
}

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [businessMenuOpen, setBusinessMenuOpen] = useState(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { webapps, activeWebapp, setActiveWebapp } = useWebapp();

  const segment = pathname.split('/').filter(Boolean).pop() || 'dashboard';
  const pageTitle = PAGE_TITLES[segment] ?? 'Dashboard';
  const userLabel = user?.name ?? user?.email ?? 'User';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#06070A] text-white">
      <div className="hidden md:flex">
        <Sidebar pathname={pathname} userLabel={userLabel} />
      </div>

      <AnimatePresence>
        {sidebarOpen ? (
          <>
            <motion.button
              type="button"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 md:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: 'tween', duration: 0.2 }}
              className="fixed inset-y-0 left-0 z-50 md:hidden"
            >
              <Sidebar pathname={pathname} userLabel={userLabel} isOpen onClose={() => setSidebarOpen(false)} />
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-[#1E2130] bg-[#141720] px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-2 text-slate-300 hover:bg-white/5 hover:text-white md:hidden"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-base font-semibold text-white sm:text-lg">{pageTitle}</h1>
              <p className="hidden text-xs text-slate-400 sm:block">Business-first beta flow</p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/dashboard/businesses/new"
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-blue-500"
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">Add Business</span>
            </Link>

            {webapps.length > 0 ? (
              <div className="relative hidden sm:block">
                <button
                  type="button"
                  onClick={() => setBusinessMenuOpen((open) => !open)}
                  className="flex items-center gap-2 rounded-xl border border-[#252A3A] bg-[#0D0F14] px-3 py-2 text-sm text-slate-200"
                >
                  <Building2 className="h-4 w-4 text-blue-300" />
                  <span className="max-w-[180px] truncate">{activeWebapp?.name || activeWebapp?.url || 'Select business'}</span>
                  <ChevronDown className={`h-4 w-4 text-slate-400 transition ${businessMenuOpen ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {businessMenuOpen ? (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="absolute right-0 top-full z-50 mt-2 w-72 rounded-2xl border border-[#252A3A] bg-[#0D0F14] p-2 shadow-2xl"
                    >
                      {webapps.map((webapp) => (
                        <button
                          key={webapp.id}
                          type="button"
                          onClick={() => {
                            setActiveWebapp(webapp.id);
                            setBusinessMenuOpen(false);
                            navigate(`/dashboard/businesses/${webapp.id}`);
                          }}
                          className={`flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left text-sm transition ${
                            activeWebapp?.id === webapp.id
                              ? 'bg-blue-500/15 text-blue-300'
                              : 'text-slate-300 hover:bg-white/5 hover:text-white'
                          }`}
                        >
                          <Building2 className="mt-0.5 h-4 w-4 flex-shrink-0" />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate font-medium">{webapp.name || 'Business profile'}</span>
                            <span className="block truncate text-xs text-slate-400">{webapp.url || 'No website yet'}</span>
                          </span>
                        </button>
                      ))}
                      <Link
                        to="/dashboard/businesses"
                        onClick={() => setBusinessMenuOpen(false)}
                        className="mt-2 flex items-center gap-2 rounded-xl px-3 py-2 text-xs text-slate-400 transition hover:bg-white/5 hover:text-white"
                      >
                        <Building2 className="h-4 w-4" />
                        Manage businesses
                      </Link>
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              </div>
            ) : null}

            <ThemeToggle />
            <button type="button" className="rounded-lg p-2 text-slate-300 hover:bg-white/5 hover:text-white">
              <Bell className="h-5 w-5" />
            </button>

            <div className="relative">
              <button
                type="button"
                onClick={() => setUserMenuOpen((open) => !open)}
                className="flex items-center gap-2 rounded-lg p-2 hover:bg-white/5"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full border border-blue-500/30 bg-blue-500/10">
                  <User className="h-4 w-4 text-blue-300" />
                </div>
                <ChevronDown className={`h-4 w-4 text-slate-400 transition ${userMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {userMenuOpen ? (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="absolute right-0 top-full z-50 mt-2 w-56 rounded-2xl border border-[#252A3A] bg-[#0D0F14] p-2 shadow-2xl"
                  >
                    <div className="border-b border-[#1E2130] px-3 py-2">
                      <p className="truncate text-sm font-medium text-white">{userLabel}</p>
                      <p className="truncate text-xs text-slate-400">{user?.email}</p>
                    </div>
                    <Link
                      to="/dashboard/settings"
                      onClick={() => setUserMenuOpen(false)}
                      className="mt-2 flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"
                    >
                      <Settings className="h-4 w-4" />
                      Settings
                    </Link>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="mt-1 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-300 transition hover:bg-red-500/10 hover:text-red-300"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign out
                    </button>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="p-4 sm:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
