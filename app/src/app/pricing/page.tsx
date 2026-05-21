import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Check, ArrowRight, Zap } from 'lucide-react';
import PublicNav from '@/components/layout/PublicNav';
import PublicFooter from '@/components/layout/PublicFooter';
import ParticleBackground from '@/components/ui/ParticleBackground';
import { getStoredToken } from '@/lib/auth';

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const PLANS = [
  {
    name: 'Starter',
    planId: 'free',
    monthlyPrice: 29,
    annualPrice: 23,
    desc: 'For solo marketers getting started with AI-powered content.',
    features: [
      '3 social platforms',
      '50 posts per month',
      'AI Content Studio',
      'Smart Scheduler',
      'Basic analytics',
      'Email support',
    ],
    cta: 'Start for free',
    highlighted: false,
  },
  {
    name: 'Pro',
    planId: 'pro',
    monthlyPrice: 79,
    annualPrice: 63,
    desc: 'For growing teams that need the full AI marketing toolkit.',
    features: [
      '10 social platforms',
      'Unlimited posts',
      'All AI tools included',
      'Viral Predictor + A/B Testing',
      'Competitor Intelligence',
      'Engagement Engine',
      'Lead Management',
      'Priority support',
    ],
    cta: 'Start Pro trial',
    highlighted: true,
    badge: 'Most Popular',
  },
  {
    name: 'Business',
    planId: 'business',
    monthlyPrice: 199,
    annualPrice: 159,
    desc: 'For agencies and enterprises running marketing at scale.',
    features: [
      'Unlimited platforms',
      'Unlimited posts',
      'White-label dashboard',
      'Custom AI training',
      'Team collaboration',
      'API access',
      'Dedicated account manager',
      'SLA-backed uptime',
    ],
    cta: 'Start Business trial',
    highlighted: false,
  },
];

const FAQ = [
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. No lock-in, no cancellation fees. Cancel from your account dashboard at any time.',
  },
  {
    q: 'What AI powers the platform?',
    a: 'AmarktAI Marketing is powered by the AmarktAI Network AI infrastructure — a multi-model system optimized for marketing content generation at scale. You can optionally connect your own API keys in settings for additional providers.',
  },
  {
    q: 'What platforms are supported?',
    a: 'YouTube, TikTok, Instagram, LinkedIn, Twitter/X, Facebook, Pinterest, Reddit, Bluesky, Telegram, Snapchat, Discord — and more being added regularly.',
  },
  {
    q: 'Is there a free trial?',
    a: 'Yes. All plans include a 7-day free trial — no credit card required to start.',
  },
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [billingEnabled, setBillingEnabled] = useState(false);

  useEffect(() => {
    fetch('/api/v1/billing/plans')
      .then(async (res) => (res.ok ? res.json() : { billing_enabled: false }))
      .then((data: { billing_enabled?: boolean }) => setBillingEnabled(Boolean(data.billing_enabled)))
      .catch(() => setBillingEnabled(false));
  }, []);

  return (
    <div className="min-h-screen bg-[#06070A] text-[#F0F2F8] relative overflow-hidden">
      <ParticleBackground variant="stars" opacity={0.2} />
      <PublicNav />

      {/* Hero */}
      <section className="py-24 px-4 sm:px-6 text-center">
        <motion.div variants={stagger} initial="hidden" animate="visible">
          <motion.p variants={fadeUp} className="text-blue-500 text-sm font-semibold uppercase tracking-widest mb-4">
            Pricing
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-4xl sm:text-5xl font-bold text-white mb-4">
            Simple, transparent pricing
          </motion.h1>
          <motion.p variants={fadeUp} className="text-[#9AA3B8] text-xl max-w-xl mx-auto mb-10">
            Start free. Scale when you're ready. No surprises.
          </motion.p>

          {/* Toggle */}
          <motion.div variants={fadeUp} className="inline-flex items-center gap-3 bg-[#0D0F14] border border-[#252A3A] rounded-full p-1">
            <button
              onClick={() => setAnnual(false)}
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${!annual ? 'bg-blue-600 text-white' : 'text-[#9AA3B8] hover:text-white'}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${annual ? 'bg-blue-600 text-white' : 'text-[#9AA3B8] hover:text-white'}`}
            >
              Annual
              <span className="bg-emerald-400/20 text-emerald-400 text-xs px-2 py-0.5 rounded-full">-20%</span>
            </button>
          </motion.div>
        </motion.div>
      </section>

      {/* Plans */}
      <section className="pb-24 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            {PLANS.map((plan) => (
              <motion.div
                key={plan.name}
                variants={fadeUp}
                className={`relative rounded-2xl p-8 flex flex-col ${
                  plan.highlighted
                    ? 'bg-blue-600/10 border-2 border-blue-600/50'
                    : 'bg-[#0D0F14] border border-[#252A3A]'
                }`}
              >
                {plan.badge && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                    <span className="bg-blue-600 text-white text-xs font-bold px-4 py-1.5 rounded-full flex items-center gap-1.5">
                      <Zap className="w-3 h-3" />
                      {plan.badge}
                    </span>
                  </div>
                )}

                <div className="mb-6">
                  <h2 className="text-white font-bold text-xl mb-1">{plan.name}</h2>
                  <p className="text-[#9AA3B8] text-sm">{plan.desc}</p>
                </div>

                <div className="mb-8">
                  <span className="text-white font-black text-5xl">
                    ${annual ? plan.annualPrice : plan.monthlyPrice}
                  </span>
                  <span className="text-[#9AA3B8] text-sm ml-1">/mo</span>
                  {annual && (
                    <p className="text-emerald-400 text-xs mt-1">Billed annually</p>
                  )}
                </div>

                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-[#9AA3B8]">
                      <Check className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>

                {billingEnabled ? (
                  <button
                    onClick={async () => {
                      const token = getStoredToken();
                      if (!token || plan.planId === 'free') {
                        window.location.href = '/register';
                        return;
                      }
                      try {
                        const res = await fetch('/api/v1/billing/checkout-session', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                          body: JSON.stringify({ plan: plan.planId }),
                        });
                        const data = await res.json();
                        if (data.url) window.location.href = data.url;
                      } catch {
                        window.location.href = '/register';
                      }
                    }}
                    className={`w-full py-3 rounded-xl font-semibold text-center text-sm transition-all flex items-center justify-center gap-2 ${
                      plan.highlighted
                        ? 'bg-blue-600 hover:bg-blue-500 text-white'
                        : 'bg-[#141720] hover:bg-[#1E2130] text-white border border-[#252A3A]'
                    }`}
                  >
                    {plan.cta}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                ) : (
                  <div className="w-full rounded-xl border border-[#252A3A] bg-[#141720] px-4 py-3 text-center text-sm text-[#9AA3B8]">
                    Billing is deferred for this launch.
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>

          {/* Enterprise */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mt-6 bg-[#0D0F14] border border-[#252A3A] rounded-2xl p-8 flex flex-col sm:flex-row items-center justify-between gap-6"
          >
            <div>
              <h3 className="text-white font-bold text-xl mb-1">Enterprise</h3>
              <p className="text-[#9AA3B8]">Custom volume pricing, dedicated infrastructure, and SLA guarantees for large teams.</p>
            </div>
            <Link
              to="/contact"
              className="flex-shrink-0 bg-white/5 hover:bg-white/10 border border-[#252A3A] text-white font-semibold px-8 py-3 rounded-xl transition-all text-sm whitespace-nowrap"
            >
              Contact us
            </Link>
          </motion.div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 px-4 sm:px-6 bg-[#0D0F14]">
        <div className="max-w-3xl mx-auto">
          <motion.h2
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl font-bold text-white text-center mb-12"
          >
            Frequently asked questions
          </motion.h2>
          <motion.div
            className="space-y-4"
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            {FAQ.map((item) => (
              <motion.div
                key={item.q}
                variants={fadeUp}
                className="bg-[#06070A] border border-[#1E2130] rounded-xl p-6"
              >
                <h3 className="text-white font-semibold mb-3">{item.q}</h3>
                <p className="text-[#9AA3B8] text-sm leading-relaxed">{item.a}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-4 sm:px-6 text-center">
        <motion.div
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          <motion.h2 variants={fadeUp} className="text-3xl font-bold text-white mb-4">
            Start your 7-day free trial
          </motion.h2>
          <motion.p variants={fadeUp} className="text-[#9AA3B8] mb-8">
            No credit card required. Cancel anytime.
          </motion.p>
          <motion.div variants={fadeUp}>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-10 py-4 rounded-xl text-lg transition-all"
            >
              Start free trial
              <ArrowRight className="w-5 h-5" />
            </Link>
          </motion.div>
        </motion.div>
      </section>

      <PublicFooter />
    </div>
  );
}
