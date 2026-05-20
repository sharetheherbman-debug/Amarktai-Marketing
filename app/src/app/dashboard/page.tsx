import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  Building2,
  CheckCircle2,
  ChevronRight,
  Loader2,
  PenTool,
  Sparkles,
  Globe,
  Calendar,
} from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth';
import { useWebapp } from '@/hooks/useWebapp';
import { contentApi, settingsApi, webAppApi } from '@/lib/api';
import type { Content, ContentLibraryItem } from '@/types';

const steps = [
  { title: 'Add Business', description: 'Start with a business name, website URL, or both.', href: '/dashboard/businesses/new' },
  { title: 'Analyze Website', description: 'Scrape the website when available and enrich the profile.', href: '/dashboard/businesses' },
  { title: 'Generate Content', description: 'Create platform-ready posts from the selected business.', href: '/dashboard/content' },
  { title: 'Review / Schedule', description: 'Review output and move it into the scheduler.', href: '/dashboard/scheduler' },
];

function readinessTone(readiness: Record<string, unknown> | null) {
  if ((readiness?.full_go_live_ready as boolean | undefined) === true) {
    return {
      label: 'Generation ready',
      badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      description: 'Providers are passing and posting setup can move toward full go-live.',
    };
  }

  return {
    label: 'Limited mode',
    badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    description: 'Provider degraded. Content generation is available with fallbacks.',
  };
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { webapps, activeWebapp, loading, reload } = useWebapp();
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [recentContent, setRecentContent] = useState<Content[]>([]);
  const [recentItems, setRecentItems] = useState<ContentLibraryItem[]>([]);
  const [busyAction, setBusyAction] = useState<'analyze' | 'generate-all' | null>(null);

  const greetingName = user?.name?.split(' ')[0] ?? 'there';

  useEffect(() => {
    const load = async () => {
      // Each API call is isolated — one failure must not prevent others from loading.
      try {
        const readinessData = await settingsApi.getReadiness();
        setReadiness(readinessData);
      } catch {
        setReadiness(null);
      }

      try {
        const content = await contentApi.getAll();
        setRecentContent(content.slice(0, 8));
      } catch {
        setRecentContent([]);
      }

      try {
        const libraryItems = await contentApi.listItems();
        setRecentItems(libraryItems.slice(0, 12));
      } catch {
        setRecentItems([]);
      }
    };
    void load();
  }, []);

  const selectedContent = useMemo(() => {
    if (!activeWebapp) return recentItems.slice(0, 4);
    return recentItems.filter((item) => item.webappId === activeWebapp.id).slice(0, 4);
  }, [activeWebapp, recentItems]);
  const activeMediaJobs = useMemo(
    () => selectedContent.reduce((sum, item) => sum + item.mediaJobIds.length, 0),
    [selectedContent]
  );
  const nextRecommendedAction = useMemo(() => {
    if (!activeWebapp) return 'Add your first business profile.';
    if (selectedContent.length === 0) return 'Generate your first campaign draft for the selected business.';
    if (activeMediaJobs > 0) return 'Review active media jobs and approve completed assets.';
    return 'Open Scheduler and plan your next posts.';
  }, [activeWebapp, activeMediaJobs, selectedContent.length]);

  const tone = readinessTone(readiness);
  const providerDetails = (readiness?.provider_details as Record<string, { status?: string; message?: string }> | undefined) ?? {};
  const noProviders = Object.values(providerDetails).every((provider) => provider?.status === 'missing' || provider?.status === 'not_configured');

  const handleAnalyze = async () => {
    if (!activeWebapp) return;
    setBusyAction('analyze');
    try {
      const result = await webAppApi.refreshIntelligence(activeWebapp.id);
      const warnings = (result.intelligence?.warnings as string[] | undefined) ?? [];
      await reload();
      toast.success(warnings.length > 0 ? 'Business updated with warnings. Review the detail page.' : 'Website analysis refreshed.');
      navigate(`/dashboard/businesses/${activeWebapp.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Website analysis failed');
    } finally {
      setBusyAction(null);
    }
  };

  const handleGenerateAll = async () => {
    if (!activeWebapp) return;
    setBusyAction('generate-all');
    try {
      const result = await contentApi.generateAll({ webappId: activeWebapp.id });
      const firstError = result.warnings?.[0];
      toast.success(firstError ? `Generation finished with warnings: ${firstError}` : `Generated ${result.count} platform drafts.`);
      const content = await contentApi.getAll();
      setRecentContent(content.slice(0, 8));
      navigate('/dashboard/content');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Generate all failed');
    } finally {
      setBusyAction(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white sm:text-3xl">Good evening, {greetingName}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            This dashboard is your command center: add a business, analyze it, generate content, then review and schedule it.
          </p>
        </div>
        <Card className="border-[#252A3A] bg-[#0D0F14] lg:w-[360px]">
          <CardContent className="flex items-start justify-between gap-4 p-5">
            <div>
              <p className="text-sm font-medium text-slate-300">Readiness</p>
              <p className="mt-1 text-sm text-slate-400">{tone.description}</p>
            </div>
            <Badge className={tone.badge}>{tone.label}</Badge>
          </CardContent>
        </Card>
      </div>

       <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
        <Card className="border-[#252A3A] bg-[#0D0F14]">
          <CardHeader>
            <CardTitle>Guided launch flow</CardTitle>
            <CardDescription>Normal users should always know the next step.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {steps.map((step, index) => (
              <Link
                key={step.title}
                to={step.href}
                className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4 transition hover:border-blue-500/30 hover:bg-[#171B24]"
              >
                <div className="mb-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/15 text-sm font-semibold text-blue-300">
                  {index + 1}
                </div>
                <h2 className="font-semibold text-white">{step.title}</h2>
                <p className="mt-2 text-sm text-slate-400">{step.description}</p>
                <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-blue-300">
                  Open
                  <ChevronRight className="h-3.5 w-3.5" />
                </span>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="border-[#252A3A] bg-[#0D0F14]">
          <CardHeader>
            <CardTitle>First-run checklist</CardTitle>
            <CardDescription>Start here: Add your business.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            {[
              { done: webapps.length > 0, label: 'Add Business' },
              { done: !noProviders, label: 'Add GenX / Firecrawl keys' },
              { done: recentContent.length > 0, label: 'Generate first content' },
              { done: false, label: 'Connect social accounts for posting later' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-3 rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2.5">
                {item.done ? <CheckCircle2 className="h-4 w-4 text-emerald-300" /> : <AlertCircle className="h-4 w-4 text-amber-300" />}
                <span>{item.label}</span>
              </div>
            ))}
            {noProviders ? (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-200">
                Full automation not configured. Add GenX and Firecrawl in Integrations for higher quality generation.
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle>Autonomy status</CardTitle>
          <CardDescription>Current selected business, active media jobs, and next best action.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Selected business</p>
            <p className="mt-2 text-sm text-white">{activeWebapp?.name || 'None selected'}</p>
          </div>
          <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Active media jobs</p>
            <p className="mt-2 text-sm text-white">{activeMediaJobs}</p>
          </div>
          <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Next recommended action</p>
            <p className="mt-2 text-sm text-white">{nextRecommendedAction}</p>
          </div>
        </CardContent>
      </Card>

      {webapps.length === 0 ? (
        <Card className="border-dashed border-blue-500/30 bg-[#0D0F14]">
          <CardContent className="flex flex-col items-start gap-4 p-8">
            <div className="rounded-2xl bg-blue-500/15 p-3 text-blue-300">
              <Building2 className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Add your first business to start generating content</h2>
              <p className="mt-2 text-sm text-slate-400">You can use a business name, website URL, or both.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to="/dashboard/businesses/new">
                <Button className="bg-blue-600 hover:bg-blue-500">Add Business</Button>
              </Link>
              <Link to="/dashboard/integrations">
                <Button variant="outline" className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                  Open Integrations
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card className="border-[#252A3A] bg-[#0D0F14]">
            <CardHeader>
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <CardTitle>Selected business</CardTitle>
                  <CardDescription>Keep the user on one obvious path: analyze, generate, then review.</CardDescription>
                </div>
                <Badge className="w-fit border border-blue-500/30 bg-blue-500/15 text-blue-300">
                  {activeWebapp?.name || 'Business profile'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold text-white">{activeWebapp?.name || 'Business profile'}</h2>
                    <p className="mt-1 text-sm text-slate-400">{activeWebapp?.url || 'No website added yet'}</p>
                    <p className="mt-3 max-w-2xl text-sm text-slate-300">
                      {activeWebapp?.description || 'Add a short description if website analysis is unavailable.'}
                    </p>
                  </div>
                  <Link to={`/dashboard/businesses/${activeWebapp?.id}`}>
                    <Button variant="outline" className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                      Open details
                    </Button>
                  </Link>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <Button onClick={handleAnalyze} disabled={busyAction === 'analyze'} className="bg-blue-600 hover:bg-blue-500">
                    {busyAction === 'analyze' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Globe className="mr-2 h-4 w-4" />}
                    Analyze Website
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => navigate(`/dashboard/content?business=${activeWebapp?.id}`)}
                    className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
                  >
                    <PenTool className="mr-2 h-4 w-4" />
                    Generate Content
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleGenerateAll}
                    disabled={busyAction === 'generate-all'}
                    className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
                  >
                    {busyAction === 'generate-all' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                    Generate All Platforms
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => navigate('/dashboard/scheduler')}
                    className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    Review / Schedule
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Scrape status</p>
                  <p className="mt-2 text-sm text-white">{String((activeWebapp?.scrapedData as Record<string, unknown> | null)?.scrape_status || 'not_started').replaceAll('_', ' ')}</p>
                </div>
                <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Category</p>
                  <p className="mt-2 text-sm text-white">{activeWebapp?.category || 'Not set yet'}</p>
                </div>
                <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Target audience</p>
                  <p className="mt-2 text-sm text-white">{activeWebapp?.targetAudience || 'Needs review'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-[#252A3A] bg-[#0D0F14]">
            <CardHeader>
              <CardTitle>Recent generated content</CardTitle>
              <CardDescription>Latest output for the selected business.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {selectedContent.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-[#252A3A] bg-[#141720] p-6 text-sm text-slate-400">
                  No generated content yet. Choose a business and generate your first campaign.
                </div>
              ) : (
                selectedContent.map((item) => {
                  return (
                    <div key={item.id} className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold capitalize text-white">{item.platform}</p>
                          <p className="text-xs text-slate-400">{item.generationStatus}</p>
                        </div>
                        <Badge className={item.degraded ? 'border border-amber-500/30 bg-amber-500/15 text-amber-300' : 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300'}>
                          {item.degraded ? 'Degraded' : 'Ready'}
                        </Badge>
                      </div>
                      <p className="mt-3 line-clamp-3 text-sm text-slate-300">{item.caption || item.body || item.videoScript || item.imagePrompt || 'No body text available.'}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        {item.providerActual || 'unknown provider'} • media jobs {item.mediaJobIds.length}
                      </p>
                      <Link to="/dashboard/content" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-blue-300">
                        Open Content Studio
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
