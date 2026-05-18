import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText, TrendingUp, Users, Zap, Calendar, BarChart2,
  PenTool, ArrowRight, Activity
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import UsageWidget from '@/components/dashboard/UsageWidget';

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

interface DashboardStats {
  postsPublished: number;
  engagementRate: string;
  leadsCaptures: number;
  tokensUsed: number;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  })();

  const dateStr = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
  });

  useEffect(() => {
    const token = localStorage.getItem('amarktai_token');
    fetch('/api/v1/dashboard/stats', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((d) => setStats(d))
      .catch(() => {
        // Graceful fallback with stub stats
        setStats({ postsPublished: 0, engagementRate: '—', leadsCaptures: 0, tokensUsed: 0 });
      })
      .finally(() => setLoading(false));
  }, []);

  const STAT_CARDS = [
    { label: 'Posts Published', value: loading ? '—' : String(stats?.postsPublished ?? 0), icon: FileText, color: 'text-blue-400 bg-blue-400/10' },
    { label: 'Engagement Rate', value: loading ? '—' : (stats?.engagementRate ?? '—'), icon: TrendingUp, color: 'text-emerald-400 bg-emerald-400/10' },
    { label: 'Leads Captured', value: loading ? '—' : String(stats?.leadsCaptures ?? 0), icon: Users, color: 'text-purple-400 bg-purple-400/10' },
    { label: 'AI Tokens Used', value: loading ? '—' : String(stats?.tokensUsed ?? 0), icon: Zap, color: 'text-orange-400 bg-orange-400/10' },
  ];

  const QUICK_ACTIONS = [
    { label: 'Generate Content', desc: 'Create posts with AI', href: '/dashboard/content', icon: PenTool, color: 'text-blue-400' },
    { label: 'View Scheduler', desc: 'Manage posting schedule', href: '/dashboard/scheduler', icon: Calendar, color: 'text-cyan-400' },
    { label: 'Check Analytics', desc: 'See your performance', href: '/dashboard/analytics', icon: BarChart2, color: 'text-purple-400' },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div variants={stagger} initial="hidden" animate="visible">
        <motion.div variants={fadeUp} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-white font-bold text-2xl sm:text-3xl mb-1">
              {greeting}, {user?.name?.split(' ')[0] ?? 'there'} 👋
            </h1>
            <p className="text-[#9AA3B8] text-sm">{dateStr}</p>
          </div>
          <Link
            to="/dashboard/content"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all self-start sm:self-auto"
          >
            <PenTool className="w-4 h-4" />
            Generate Content
          </Link>
        </motion.div>
      </motion.div>

      {/* Usage */}
      <UsageWidget />

      {/* Stats */}
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {STAT_CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={card.label}
              variants={fadeUp}
              className="bg-[#0D0F14] border border-[#1E2130] rounded-2xl p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <p className="text-[#9AA3B8] text-sm">{card.label}</p>
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${card.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <p className="text-white font-bold text-2xl">
                {loading ? (
                  <span className="inline-block w-12 h-6 bg-[#1E2130] rounded animate-pulse" />
                ) : card.value}
              </p>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        <motion.h2 variants={fadeUp} className="text-white font-semibold mb-4">Quick Actions</motion.h2>
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-3 gap-4"
          variants={stagger}
        >
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <motion.div key={action.label} variants={fadeUp}>
                <Link
                  to={action.href}
                  className="group flex items-center gap-4 bg-[#0D0F14] hover:bg-[#141720] border border-[#1E2130] hover:border-[#252A3A] rounded-2xl p-5 transition-all"
                >
                  <div className={`w-10 h-10 rounded-xl bg-[#141720] group-hover:bg-[#1E2130] flex items-center justify-center flex-shrink-0 transition-all ${action.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium text-sm">{action.label}</p>
                    <p className="text-[#5A6478] text-xs">{action.desc}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-[#5A6478] group-hover:text-[#9AA3B8] flex-shrink-0 transition-colors" />
                </Link>
              </motion.div>
            );
          })}
        </motion.div>
      </motion.div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" />
            Recent Activity
          </h2>
        </div>
        <div className="bg-[#0D0F14] border border-[#1E2130] rounded-2xl overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="w-8 h-8 border-2 border-[#252A3A] border-t-blue-600 rounded-full animate-spin mx-auto" />
            </div>
          ) : (
            <div className="p-6">
              <div className="text-center py-8">
                <p className="text-[#5A6478] text-sm">
                  Activity will appear here once you start creating and scheduling content.
                </p>
                <Link
                  to="/dashboard/content"
                  className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-sm font-medium mt-3 transition-colors"
                >
                  Generate your first post
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
