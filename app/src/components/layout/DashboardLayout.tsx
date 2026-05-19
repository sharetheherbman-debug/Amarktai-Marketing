import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home, PenTool, CheckSquare, Calendar, BarChart2,
  MessageCircle, Share2, Zap, Users, FileText,
  Plug, Settings, Shield, Menu, X, Bell, ChevronDown,
  LogOut, User, Building2,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { useWebapp } from '@/hooks/useWebapp';
import ThemeToggle from '@/components/ui/ThemeToggle';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

const NAV_SECTIONS = [
  {
    label: 'Core',
    items: [
      { label: 'Dashboard', href: '/dashboard', icon: Home },
      { label: 'Content Studio', href: '/dashboard/content', icon: PenTool },
      { label: 'Approval Queue', href: '/dashboard/approval', icon: CheckSquare },
      { label: 'Scheduler', href: '/dashboard/scheduler', icon: Calendar },
    ] as NavItem[],
  },
  {
    label: 'Intelligence',
    items: [
      { label: 'Analytics', href: '/dashboard/analytics', icon: BarChart2 },
      { label: 'Engagement', href: '/dashboard/engagement', icon: MessageCircle },
      { label: 'Platforms', href: '/dashboard/platforms', icon: Share2 },
    ] as NavItem[],
  },
  {
    label: 'Tools',
    items: [
      { label: 'AI Tools', href: '/dashboard/tools', icon: Zap },
      { label: 'Blog', href: '/dashboard/blog', icon: FileText },
      { label: 'Leads', href: '/dashboard/leads', icon: Users },
    ] as NavItem[],
  },
  {
    label: 'System',
    items: [
      { label: 'Integrations', href: '/dashboard/integrations', icon: Plug },
      { label: 'Settings', href: '/dashboard/settings', icon: Settings },
      { label: 'Admin', href: '/dashboard/admin', icon: Shield, adminOnly: true },
    ] as NavItem[],
  },
];

function NavLink({ item, isActive, onClick }: { item: NavItem; isActive: boolean; onClick?: () => void }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.href}
      onClick={onClick}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
        isActive
          ? 'bg-blue-600/15 text-blue-400 border border-blue-600/20'
          : 'text-[#9AA3B8] hover:text-white hover:bg-white/5'
      }`}
    >
      <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-blue-400' : ''}`} />
      {item.label}
    </Link>
  );
}

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [webappMenuOpen, setWebappMenuOpen] = useState(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { webapps, activeWebapp, setActiveWebapp } = useWebapp();

  const isAdmin = user?.isAdmin || false;

  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const pageTitle = (() => {
    const seg = pathname.split('/').filter(Boolean).pop() || 'dashboard';
    const map: Record<string, string> = {
      dashboard: 'Dashboard',
      content: 'Content Studio',
      approval: 'Approval Queue',
      scheduler: 'Scheduler',
      analytics: 'Analytics',
      engagement: 'Engagement',
      platforms: 'Platforms',
      tools: 'AI Tools',
      blog: 'SEO Blog',
      leads: 'Leads',
      integrations: 'Integrations',
      settings: 'Settings',
      admin: 'Admin',
    };
    return map[seg] ?? 'Dashboard';
  })();

  const Sidebar = ({ onClose }: { onClose?: () => void }) => (
    <aside className="flex flex-col h-full bg-[#0D0F14] border-r border-[#1E2130] w-64">
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-[#1E2130]">
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-white font-bold text-sm">
            <span className="whitespace-nowrap">Amarkt<span className="text-blue-500">AI</span></span> Marketing
          </span>
        </Link>
        {onClose && (
          <button onClick={onClose} className="text-[#5A6478] hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <p className="text-[#5A6478] text-xs font-semibold uppercase tracking-widest mb-2 px-3">
              {section.label}
            </p>
            <div className="space-y-1">
              {section.items
                .filter((item) => !item.adminOnly || isAdmin)
                .map((item) => (
                  <NavLink
                    key={item.href}
                    item={item}
                    isActive={pathname === item.href}
                    onClick={onClose}
                  />
                ))}
            </div>
          </div>
        ))}
      </nav>

      {/* User */}
      <div className="p-4 border-t border-[#1E2130]">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#141720]">
          <div className="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-600/30 flex items-center justify-center flex-shrink-0">
            <User className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">{user?.name ?? user?.email ?? 'User'}</p>
            <p className="text-[#5A6478] text-xs">Beta</p>
          </div>
        </div>
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-[#06070A]">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 md:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -256 }}
              animate={{ x: 0 }}
              exit={{ x: -256 }}
              transition={{ type: 'tween', duration: 0.2 }}
              className="fixed left-0 top-0 bottom-0 z-50 md:hidden"
            >
              <Sidebar onClose={() => setSidebarOpen(false)} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="flex-shrink-0 h-16 bg-[#141720] border-b border-[#1E2130] flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden p-2 text-[#9AA3B8] hover:text-white transition-colors"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-white font-semibold text-base">{pageTitle}</h1>
          </div>

          <div className="flex items-center gap-2">
            {/* Webapp Switcher */}
            {webapps.length > 0 && (
              <div className="relative hidden sm:block">
                <button
                  onClick={() => setWebappMenuOpen(!webappMenuOpen)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-white/5 text-sm text-[#9AA3B8] hover:text-white transition-colors border border-[#252A3A]"
                >
                  <Building2 className="w-3.5 h-3.5" />
                  <span className="max-w-[120px] truncate">{activeWebapp?.name ?? 'Select Business'}</span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${webappMenuOpen ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {webappMenuOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.1 }}
                      className="absolute right-0 top-full mt-1 w-56 bg-[#0D0F14] border border-[#252A3A] rounded-xl shadow-xl z-50 overflow-hidden"
                    >
                      <div className="p-1">
                        {webapps.map((w) => (
                          <button
                            key={w.id}
                            onClick={() => { setActiveWebapp(w.id); setWebappMenuOpen(false); }}
                            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left ${
                              activeWebapp?.id === w.id
                                ? 'bg-blue-600/15 text-blue-400'
                                : 'text-[#9AA3B8] hover:text-white hover:bg-white/5'
                            }`}
                          >
                            <Building2 className="w-3.5 h-3.5 flex-shrink-0" />
                            <span className="truncate">{w.name}</span>
                          </button>
                        ))}
                        <div className="border-t border-[#1E2130] mt-1 pt-1">
                          <Link
                            to="/dashboard/webapps"
                            onClick={() => setWebappMenuOpen(false)}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-[#5A6478] hover:text-white hover:bg-white/5 transition-colors"
                          >
                            + Manage businesses
                          </Link>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            <ThemeToggle />

            <button className="p-2 text-[#9AA3B8] hover:text-white transition-colors rounded-lg hover:bg-white/5 relative">
              <Bell className="w-5 h-5" />
            </button>

            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-600/30 flex items-center justify-center">
                  <User className="w-3.5 h-3.5 text-blue-400" />
                </div>
                <ChevronDown className={`w-4 h-4 text-[#9AA3B8] transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {userMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.1 }}
                    className="absolute right-0 top-full mt-1 w-52 bg-[#0D0F14] border border-[#252A3A] rounded-xl shadow-xl z-50 overflow-hidden"
                  >
                    <div className="p-3 border-b border-[#1E2130]">
                      <p className="text-white text-sm font-medium truncate">{user?.name ?? user?.email ?? 'User'}</p>
                      <p className="text-[#5A6478] text-xs truncate">{user?.email}</p>
                    </div>
                    <div className="p-1">
                      <Link
                        to="/dashboard/settings"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-[#9AA3B8] hover:text-white hover:bg-white/5 transition-colors"
                      >
                        <Settings className="w-4 h-4" />
                        Settings
                      </Link>
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-[#9AA3B8] hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        Sign Out
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 sm:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
