import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  Globe,
  Loader2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { contentApi, webAppApi } from '@/lib/api';
import type { Content, Platform, WebApp } from '@/types';

const platforms: Array<{ id: Platform; label: string }> = [
  { id: 'instagram', label: 'Generate Instagram' },
  { id: 'facebook', label: 'Generate Facebook' },
  { id: 'linkedin', label: 'Generate LinkedIn' },
  { id: 'twitter', label: 'Generate X / Twitter' },
];

export default function BusinessDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [business, setBusiness] = useState<WebApp | null>(null);
  const [recentContent, setRecentContent] = useState<Content[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const load = async () => {
    if (!id) return;
    try {
      const [businessData, content] = await Promise.all([
        webAppApi.getById(id),
        contentApi.getAll(),
      ]);
      if (!businessData) {
        toast.error('Business not found');
        navigate('/dashboard/businesses');
        return;
      }
      setBusiness(businessData);
      setRecentContent(content.filter((item) => item.webappId === businessData.id).slice(0, 6));
    } catch {
      toast.error('Failed to load business');
      navigate('/dashboard/businesses');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [id]);

  const intelligence = useMemo(() => ((business?.scrapedData as Record<string, unknown> | null | undefined) ?? null), [business]);
  const warnings = ((intelligence?.warnings as string[] | undefined) ?? []).filter(Boolean);

  const handleRefresh = async () => {
    if (!business) return;
    setBusyAction('refresh');
    try {
      const result = await webAppApi.refreshIntelligence(business.id);
      const nextWarnings = (result.intelligence?.warnings as string[] | undefined) ?? [];
      toast.success(nextWarnings.length > 0 ? 'Website analysis refreshed with warnings.' : 'Website analysis refreshed.');
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Website analysis failed');
    } finally {
      setBusyAction(null);
    }
  };

  const handleGenerate = async (platform: Platform) => {
    if (!business) return;
    setBusyAction(platform);
    try {
      await contentApi.generate(business.id, platform);
      toast.success(`${platform} draft created.`);
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Content generation failed');
    } finally {
      setBusyAction(null);
    }
  };

  const handleGenerateAll = async () => {
    if (!business) return;
    setBusyAction('all');
    try {
      const result = await contentApi.generateAll({ webappId: business.id });
      toast.success(result.warnings?.[0] ? `Generate all finished with warnings: ${result.warnings[0]}` : `Generated ${result.count} drafts.`);
      await load();
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

  if (!business) return null;

  return (
    <div className="space-y-6">
      <Link to="/dashboard/businesses" className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white">
        <ArrowLeft className="h-4 w-4" />
        Back to Businesses
      </Link>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-white">
                <Building2 className="h-5 w-5 text-blue-300" />
                {business.name || 'Business profile'}
              </CardTitle>
              <CardDescription className="mt-2 text-slate-400">{business.url || 'No website URL yet'}</CardDescription>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={handleRefresh} disabled={busyAction === 'refresh'} className="bg-blue-600 hover:bg-blue-500">
                {busyAction === 'refresh' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Globe className="mr-2 h-4 w-4" />}
                Analyze / Refresh Website
              </Button>
              <Button
                variant="outline"
                onClick={handleGenerateAll}
                disabled={busyAction === 'all'}
                className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
              >
                {busyAction === 'all' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                Generate All Platforms
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-4">
              <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-5">
                <p className="text-xs uppercase tracking-wide text-slate-500">Description</p>
                <p className="mt-2 text-sm text-slate-200">{business.description || 'No description yet.'}</p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-5">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Extracted summary</p>
                  <p className="mt-2 text-sm text-slate-200">{String(intelligence?.page_summary || business.description || 'No summary extracted.')}</p>
                </div>
                <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-5">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Audience</p>
                  <p className="mt-2 text-sm text-slate-200">{String(intelligence?.target_audience_guess || business.targetAudience || 'No audience extracted.')}</p>
                </div>
                <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-5">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Services</p>
                  <p className="mt-2 text-sm text-slate-200">{((intelligence?.products_services as string[] | undefined) ?? business.keyFeatures ?? []).join(', ') || 'No services extracted.'}</p>
                </div>
                <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-5">
                  <p className="text-xs uppercase tracking-wide text-slate-500">CTAs</p>
                  <p className="mt-2 text-sm text-slate-200">{((intelligence?.ctas as string[] | undefined) ?? []).join(', ') || 'No CTAs extracted.'}</p>
                </div>
              </div>

              <div className="rounded-2xl border border-[#252A3A] bg-[#141720] p-5">
                <p className="text-xs uppercase tracking-wide text-slate-500">Keywords</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(((intelligence?.keywords as string[] | undefined) ?? []).length > 0 ? (intelligence?.keywords as string[]) : ['No keywords extracted yet']).map((keyword) => (
                    <Badge key={keyword} className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>

              {warnings.length > 0 ? (
                <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-100">
                  <div className="flex items-center gap-2 font-medium">
                    <AlertCircle className="h-4 w-4" />
                    Website analysis failed, but the business profile was created. Add a description or try refresh.
                  </div>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
                    {warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>

            <div className="space-y-4">
              <Card className="border-[#252A3A] bg-[#141720]">
                <CardHeader>
                  <CardTitle className="text-base text-white">Generate platform content</CardTitle>
                  <CardDescription>Social OAuth is only needed for posting later.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {platforms.map((platform) => (
                    <Button
                      key={platform.id}
                      variant="outline"
                      onClick={() => handleGenerate(platform.id)}
                      disabled={busyAction === platform.id}
                      className="w-full justify-start border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
                    >
                      {busyAction === platform.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                      {platform.label}
                    </Button>
                  ))}
                  <Link to={`/dashboard/content?business=${business.id}`} className="block">
                    <Button className="mt-2 w-full bg-blue-600 hover:bg-blue-500">Open Content Studio</Button>
                  </Link>
                </CardContent>
              </Card>

              <Card className="border-[#252A3A] bg-[#141720]">
                <CardHeader>
                  <CardTitle className="text-base text-white">Recent drafts</CardTitle>
                  <CardDescription>Latest content generated for this business.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {recentContent.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-[#252A3A] bg-[#0D0F14] p-4 text-sm text-slate-400">
                      No drafts yet. Generate Instagram, Facebook, LinkedIn, X/Twitter, or all launch platforms.
                    </div>
                  ) : (
                    recentContent.map((item) => {
                      const metadata = (item.generationMetadata as Record<string, unknown> | undefined) ?? {};
                      const degraded = Boolean(metadata.degraded);
                      return (
                        <div key={item.id} className="rounded-xl border border-[#252A3A] bg-[#0D0F14] p-4">
                          <div className="flex items-center justify-between gap-2">
                            <p className="font-medium capitalize text-white">{item.platform}</p>
                            <Badge className={degraded ? 'border border-amber-500/30 bg-amber-500/15 text-amber-300' : 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300'}>
                              {degraded ? 'Degraded' : 'Ready'}
                            </Badge>
                          </div>
                          <p className="mt-2 line-clamp-3 text-sm text-slate-300">{item.caption}</p>
                          <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                            {Boolean(metadata.scrape_status) ? <span>Scrape: {String(metadata.scrape_status)}</span> : null}
                            {Boolean(metadata.generation_status) ? <span>• {String(metadata.generation_status).replaceAll('_', ' ')}</span> : null}
                          </div>
                        </div>
                      );
                    })
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
