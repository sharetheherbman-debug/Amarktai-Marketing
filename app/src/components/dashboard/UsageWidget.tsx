import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BarChart3, ArrowUpRight } from 'lucide-react';
import { getStoredToken } from '@/lib/auth';

interface BillingInfo {
  plan_tier: string;
  effective_plan?: string;
  quota_used: number;
  quota_limit: number;
  quota_remaining: number;
  is_admin?: boolean;
  billing_enabled?: boolean;
}

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function UsageWidget() {
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    fetch('/api/v1/settings/billing', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((d: BillingInfo) => setBilling(d))
      .catch(() => {
        setBilling({
          plan_tier: 'free',
          quota_used: 0,
          quota_limit: 50,
          quota_remaining: 50,
          billing_enabled: false,
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const pct =
    billing && billing.quota_limit > 0
      ? Math.min(Math.round((billing.quota_used / billing.quota_limit) * 100), 100)
      : 0;

  const isFree = (billing?.effective_plan ?? billing?.plan_tier ?? 'free').toLowerCase() === 'free';
  const showUpgrade = isFree && billing?.billing_enabled && !billing?.is_admin;

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      className="bg-[#0D0F14]/80 border border-[#1A1F2E] rounded-2xl p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-blue-400" />
          </div>
          <h3 className="text-white font-semibold text-sm">Usage</h3>
        </div>
        {billing && (
          <span className="text-[#5A6478] text-xs capitalize">
            {billing.plan_tier} plan
          </span>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          <div className="h-4 w-32 bg-[#1E2130] rounded animate-pulse" />
          <div className="h-2 w-full bg-[#1E2130] rounded-full animate-pulse" />
        </div>
      ) : (
        <>
          <p className="text-white text-sm mb-2">
            <span className="font-bold">{billing?.quota_used ?? 0}</span>
            <span className="text-[#5A6478]"> / {billing?.quota_limit ?? 0} posts used</span>
          </p>

          {/* Progress bar */}
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-[#1E2130]">
            <motion.div
              className={`h-full rounded-full ${
                pct >= 90
                  ? 'bg-red-500'
                  : pct >= 70
                    ? 'bg-amber-500'
                    : 'bg-blue-500'
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>

          <p className="text-[#5A6478] text-xs mt-2">
            {billing?.quota_remaining ?? 0} posts remaining
          </p>

          {showUpgrade && (
            <Link
              to="/pricing"
              className="mt-3 inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              Upgrade
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </>
      )}
    </motion.div>
  );
}
