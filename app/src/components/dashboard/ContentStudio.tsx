import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Copy, Loader2, PenTool, Save, Send, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { contentApi, webAppApi } from '@/lib/api';
import type { Content, Platform, WebApp } from '@/types';

const platforms: Array<{ id: Platform; label: string }> = [
  { id: 'instagram', label: 'Instagram' },
  { id: 'facebook', label: 'Facebook' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'twitter', label: 'X / Twitter' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'reddit', label: 'Reddit' },
  { id: 'pinterest', label: 'Pinterest' },
];

const creativeSuiteSections = [
  'Campaign Plan',
  'Platform Posts',
  'Images / Creatives',
  'Video / Shorts',
  'YouTube Kit',
  'TikTok / Reels Kit',
  'Talking Avatar',
  'Full Campaign Pack',
  'Calendar / Schedule Plan',
  'Learning Insights',
];

export function ContentStudio({
  initialBusinessId,
  onGenerated,
}: {
  initialBusinessId?: string;
  onGenerated?: (items: Content[]) => void;
}) {
  const [businesses, setBusinesses] = useState<WebApp[]>([]);
  const [businessId, setBusinessId] = useState(initialBusinessId ?? '');
  const [platform, setPlatform] = useState<Platform>('instagram');
  const [objective, setObjective] = useState('');
  const [tone, setTone] = useState('');
  const [audience, setAudience] = useState('');
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<'single' | 'all' | null>(null);
  const [apiError, setApiError] = useState<string>('');
  const [generated, setGenerated] = useState<Content[]>([]);

  useEffect(() => {
    const loadBusinesses = async () => {
      try {
        const items = await webAppApi.getAll();
        setBusinesses(items);
        setBusinessId((current) => {
          if (items.length === 0) return '';
          if (current && items.some((item) => item.id === current)) return current;
          if (initialBusinessId && items.some((item) => item.id === initialBusinessId)) return initialBusinessId;
          return items[0].id;
        });
      } catch (error) {
        setApiError(error instanceof Error ? error.message : 'Failed to load businesses.');
      } finally {
        setLoading(false);
      }
    };
    void loadBusinesses();
    const handler = () => {
      void loadBusinesses();
    };
    window.addEventListener('amarktai:webapps-changed', handler);
    return () => window.removeEventListener('amarktai:webapps-changed', handler);
  }, [initialBusinessId]);

  const selectedBusiness = useMemo(() => businesses.find((item) => item.id === businessId) ?? null, [businessId, businesses]);

  const handleGenerate = async () => {
    if (!businessId) {
      setApiError('Add or select a business before generating content.');
      return;
    }

    setBusyAction('single');
    setApiError('');
    try {
      const item = await contentApi.generate(businessId, platform, {
        objective: objective.trim() || undefined,
        tone: tone.trim() || undefined,
        audience: audience.trim() || undefined,
      });
      const next = [item, ...generated].slice(0, 8);
      setGenerated(next);
      onGenerated?.([item]);
      toast.success(`${platform} draft created.`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : 'Generation failed.');
    } finally {
      setBusyAction(null);
    }
  };

  const handleGenerateAll = async () => {
    if (!businessId) {
      setApiError('Add or select a business before generating content.');
      return;
    }

    setBusyAction('all');
    setApiError('');
    try {
      const batch = await contentApi.generateAll({ webappId: businessId });
      const items = batch.items.filter((item): item is Record<string, unknown> => !('error' in item));
      const loadedItems = await Promise.all(
        items
          .map((item) => String(item.id || ''))
          .filter(Boolean)
          .map((id) => contentApi.getById(id))
      );
      const next = loadedItems.filter((item): item is Content => Boolean(item));
      setGenerated((current) => [...next, ...current].slice(0, 12));
      onGenerated?.(next);
      toast.success(batch.warnings?.[0] ? `Generated with warnings: ${batch.warnings[0]}` : `Generated ${next.length} platform drafts.`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : 'Generate all failed.');
    } finally {
      setBusyAction(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[240px] items-center justify-center rounded-2xl border border-[#252A3A] bg-[#0D0F14]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
      </div>
    );
  }

  if (businesses.length === 0) {
    return (
      <Card className="border-dashed border-blue-500/30 bg-[#0D0F14]">
        <CardContent className="flex flex-col items-start gap-4 p-8">
          <div className="rounded-2xl bg-blue-500/15 p-3 text-blue-300">
            <PenTool className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white">Add Business</h3>
            <p className="mt-2 text-sm text-slate-400">Content Studio needs a real business profile before generation controls become available.</p>
          </div>
          <Link to="/dashboard/businesses/new">
            <Button className="bg-blue-600 hover:bg-blue-500">Add Business</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle>Creative Suite</CardTitle>
          <CardDescription>Production workspace sections with truthful capability state.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {creativeSuiteSections.map((section) => (
            <div key={section} className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
              <p className="text-sm font-medium text-white">{section}</p>
              <p className="mt-1 text-xs text-slate-400">{section === 'Talking Avatar' ? 'Needs provider' : 'Ready / Limited mode'}</p>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle>Generate content</CardTitle>
          <CardDescription>Generation works from the business profile even without social OAuth. OAuth is only for posting later.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {apiError ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              <div className="flex items-center gap-2 font-medium">
                <AlertCircle className="h-4 w-4" />
                API error
              </div>
              <p className="mt-2">{apiError}</p>
            </div>
          ) : null}

          <div className="grid gap-5 lg:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-slate-200">Business</Label>
              <select
                value={businessId}
                onChange={(event) => setBusinessId(event.target.value)}
                className="w-full rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2.5 text-sm text-white"
              >
                {businesses.map((business) => (
                  <option key={business.id} value={business.id}>
                    {business.name || business.url || business.id}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label className="text-slate-200">Platform</Label>
              <select
                value={platform}
                onChange={(event) => setPlatform(event.target.value as Platform)}
                className="w-full rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2.5 text-sm text-white"
              >
                {platforms.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="objective" className="text-slate-200">Objective</Label>
              <Input
                id="objective"
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                placeholder="Drive leads, book demos, grow awareness"
                className="border-[#252A3A] bg-[#141720] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tone" className="text-slate-200">Tone</Label>
              <Input
                id="tone"
                value={tone}
                onChange={(event) => setTone(event.target.value)}
                placeholder="Confident, friendly, premium"
                className="border-[#252A3A] bg-[#141720] text-white"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="audience" className="text-slate-200">Audience override</Label>
            <Textarea
              id="audience"
              value={audience}
              onChange={(event) => setAudience(event.target.value)}
              placeholder="Optional audience context for this campaign"
              className="min-h-[100px] border-[#252A3A] bg-[#141720] text-white"
            />
          </div>

          <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-4 text-sm text-slate-300">
            <p className="font-medium text-white">Selected business</p>
            <p className="mt-1">{selectedBusiness?.name || 'Business profile'}</p>
            <p className="mt-2 text-slate-400">{selectedBusiness?.description || 'No description yet. Website analysis or manual notes will improve generation.'}</p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={handleGenerate} disabled={busyAction !== null} className="bg-blue-600 hover:bg-blue-500">
              {busyAction === 'single' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              Generate Content
            </Button>
            <Button
              variant="outline"
              onClick={handleGenerateAll}
              disabled={busyAction !== null}
              className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
            >
              {busyAction === 'all' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              Generate All Platforms
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        {generated.length === 0 ? (
          <Card className="border-dashed border-[#252A3A] bg-[#0D0F14] xl:col-span-2">
            <CardContent className="p-6 text-sm text-slate-400">
              Generated output will show platform, caption/body, CTA, hashtags, generation status, degraded warnings, scrape source, and quick actions.
            </CardContent>
          </Card>
        ) : (
          generated.map((item) => {
            const metadata = (item.generationMetadata as Record<string, unknown> | undefined) ?? {};
            const hashtags = Array.isArray(metadata.hashtags) && metadata.hashtags.length > 0 ? (metadata.hashtags as string[]) : item.hashtags;
            const degraded = Boolean(metadata.degraded);
            return (
              <Card key={item.id} className="border-[#252A3A] bg-[#0D0F14]">
                <CardHeader>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base capitalize text-white">{item.platform}</CardTitle>
                      <CardDescription>{item.title || 'Generated draft'}</CardDescription>
                    </div>
                    <Badge className={degraded ? 'border border-amber-500/30 bg-amber-500/15 text-amber-300' : 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300'}>
                      {String(metadata.generation_status || item.status).replaceAll('_', ' ')}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Caption / Body</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-200">{item.caption}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">CTA</p>
                    <p className="mt-2 text-sm text-slate-200">{String(metadata.cta || 'Review CTA before approval.')}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Hashtags</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {hashtags.length > 0 ? hashtags.map((tag) => (
                        <Badge key={tag} className="border border-[#252A3A] bg-[#141720] text-slate-200">{tag}</Badge>
                      )) : <span className="text-sm text-slate-400">No hashtags</span>}
                    </div>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3 text-xs text-slate-300">
                      <p className="font-medium text-white">Generation status</p>
                      <p className="mt-1">{String(metadata.generation_status || item.status).replaceAll('_', ' ')}</p>
                      {degraded ? <p className="mt-1 text-amber-300">Fallback or template output used. Review before posting.</p> : null}
                    </div>
                    <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3 text-xs text-slate-300">
                      <p className="font-medium text-white">Scrape source / status</p>
                      <p className="mt-1">{String(metadata.scrape_provider || 'manual')} • {String(metadata.scrape_status || 'unknown')}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button
                      variant="outline"
                      onClick={() => toast.success('Draft is already saved in the content library.')}
                      className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
                    >
                      <Save className="mr-2 h-4 w-4" />
                      Save
                    </Button>
                    <Button
                      variant="outline"
                      onClick={async () => {
                        await navigator.clipboard.writeText(item.caption);
                        toast.success('Copied draft to clipboard.');
                      }}
                      className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </Button>
                    <Link to="/dashboard/approval">
                      <Button variant="outline" className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                        <Send className="mr-2 h-4 w-4" />
                        Send to Approval Queue
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
