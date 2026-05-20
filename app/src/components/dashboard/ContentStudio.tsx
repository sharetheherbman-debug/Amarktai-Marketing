import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Calendar, Copy, Loader2, PenTool, Sparkles, Trash2, Wand2, XCircle } from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { contentApi, webAppApi } from '@/lib/api';
import type { Content, ContentLibraryItem, Platform, WebApp } from '@/types';

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

function cardBody(item: ContentLibraryItem): string {
  return (
    item.caption ||
    item.imagePrompt ||
    item.videoScript ||
    item.voiceoverScript ||
    item.avatarScript ||
    item.thumbnailPrompt ||
    'No body text generated for this item yet.'
  );
}

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
  const [items, setItems] = useState<ContentLibraryItem[]>([]);
  const [filterPlatform, setFilterPlatform] = useState<string>('all');
  const [filterFormat, setFilterFormat] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('active');
  const [filterProvider, setFilterProvider] = useState<string>('all');
  const [filterDate, setFilterDate] = useState<string>('');
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');

  const selectedBusiness = useMemo(() => businesses.find((item) => item.id === businessId) ?? null, [businessId, businesses]);

  const loadBusinessItems = useCallback(async (nextBusinessId: string) => {
    if (!nextBusinessId) {
      setItems([]);
      return;
    }
    const loaded = await contentApi.getByWebapp(nextBusinessId);
    setItems(loaded);
  }, []);

  useEffect(() => {
    const loadBusinesses = async () => {
      try {
        const loadedBusinesses = await webAppApi.getAll();
        setBusinesses(loadedBusinesses);
        const nextBusinessId =
          loadedBusinesses.length === 0
            ? ''
            : (businessId && loadedBusinesses.some((item) => item.id === businessId)
              ? businessId
              : (initialBusinessId && loadedBusinesses.some((item) => item.id === initialBusinessId) ? initialBusinessId : loadedBusinesses[0].id));
        setBusinessId(nextBusinessId);
        await loadBusinessItems(nextBusinessId);
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
  }, [businessId, initialBusinessId, loadBusinessItems]);

  const refreshItems = useCallback(async () => {
    if (!businessId) return;
    await loadBusinessItems(businessId);
  }, [businessId, loadBusinessItems]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // 'active' filter hides rejected/deleted items from default view
      if (filterStatus === 'active') {
        const s = (item.status || item.generationStatus || '').toLowerCase();
        if (s === 'rejected' || s === 'deleted') return false;
      } else if (filterStatus !== 'all') {
        const s = (item.status || item.generationStatus || '').toLowerCase();
        if (s !== filterStatus) return false;
      }
      if (filterPlatform !== 'all' && item.platform !== filterPlatform) return false;
      if (filterFormat !== 'all' && item.format !== filterFormat) return false;
      if (filterProvider !== 'all' && (item.providerActual || 'unknown') !== filterProvider) return false;
      if (filterDate && !item.createdAt.startsWith(filterDate)) return false;
      return true;
    });
  }, [items, filterDate, filterFormat, filterPlatform, filterProvider, filterStatus]);

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
      onGenerated?.([item]);
      await refreshItems();
      toast.success(`${platform} draft created and saved.`);
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
      const loadedItems = await Promise.all(
        batch.items
          .map((item) => String(item.id || ''))
          .filter(Boolean)
          .map((id) => contentApi.getById(id))
      );
      onGenerated?.(loadedItems.filter((item): item is Content => item !== null));
      await refreshItems();
      toast.success(batch.warnings?.[0] ? `Generated with warnings: ${batch.warnings[0]}` : `Generated ${batch.count} platform drafts.`);
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
          <CardTitle>Content Studio</CardTitle>
          <CardDescription>Generate, review, and manage saved content drafts in one workspace.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
            <p className="text-xs text-slate-400">Selected business</p>
            <p className="mt-1 font-medium text-white">{selectedBusiness?.name || 'Business profile'}</p>
          </div>
          <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
            <p className="text-xs text-slate-400">Saved items</p>
            <p className="mt-1 font-medium text-white">{items.length}</p>
          </div>
          <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
            <p className="text-xs text-slate-400">Campaign pack items</p>
            <p className="mt-1 font-medium text-white">{items.filter((item) => item.format !== 'text_post').length}</p>
          </div>
          <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
            <p className="text-xs text-slate-400">Active media jobs</p>
            <p className="mt-1 font-medium text-white">{items.filter((item) => item.mediaJobIds.length > 0).length}</p>
          </div>
        </CardContent>
      </Card>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle>Generate content</CardTitle>
          <CardDescription>Generated results appear immediately and remain in your saved library after refresh.</CardDescription>
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
                onChange={async (event) => {
                  const nextBusinessId = event.target.value;
                  setBusinessId(nextBusinessId);
                  await loadBusinessItems(nextBusinessId);
                }}
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
              <Input id="objective" value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Drive leads, book demos, grow awareness" className="border-[#252A3A] bg-[#141720] text-white" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tone" className="text-slate-200">Tone</Label>
              <Input id="tone" value={tone} onChange={(event) => setTone(event.target.value)} placeholder="Confident, friendly, premium" className="border-[#252A3A] bg-[#141720] text-white" />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="audience" className="text-slate-200">Audience override</Label>
            <Textarea id="audience" value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="Optional audience context for this campaign" className="min-h-[100px] border-[#252A3A] bg-[#141720] text-white" />
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={handleGenerate} disabled={busyAction !== null} className="bg-blue-600 hover:bg-blue-500">
              {busyAction === 'single' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              Generate Content
            </Button>
            <Button variant="outline" onClick={handleGenerateAll} disabled={busyAction !== null} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
              {busyAction === 'all' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              Generate All Platforms
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle>Content Library</CardTitle>
          <CardDescription>Saved generated drafts, pack outputs, media states, and provider/model details.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <select value={filterPlatform} onChange={(event) => setFilterPlatform(event.target.value)} className="rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2 text-sm text-white">
              <option value="all">All platforms</option>
              {[...new Set(items.map((item) => item.platform))].map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
            <select value={filterFormat} onChange={(event) => setFilterFormat(event.target.value)} className="rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2 text-sm text-white">
              <option value="all">All formats</option>
              {[...new Set(items.map((item) => item.format))].map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
            <select value={filterStatus} onChange={(event) => setFilterStatus(event.target.value)} className="rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2 text-sm text-white">
              <option value="active">Active (hide rejected)</option>
              <option value="all">All statuses</option>
              <option value="rejected">Rejected</option>
              <option value="scheduled">Scheduled</option>
              <option value="template_fallback">Template fallback</option>
              {[...new Set(items.map((item) => item.generationStatus))].filter((v) => !['rejected', 'scheduled', 'template_fallback'].includes(v)).map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
            <select value={filterProvider} onChange={(event) => setFilterProvider(event.target.value)} className="rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2 text-sm text-white">
              <option value="all">All providers</option>
              {[...new Set(items.map((item) => item.providerActual || 'unknown'))].map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
            <Input type="date" value={filterDate} onChange={(event) => setFilterDate(event.target.value)} className="border-[#252A3A] bg-[#141720] text-white" />
          </div>

          {filteredItems.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[#252A3A] bg-[#141720] p-4 text-sm text-slate-400">
              {filterStatus === 'active'
                ? 'No active content. Generate your first campaign above, or switch to "All statuses" to see rejected/deleted items.'
                : 'No content matches your filters.'}
            </div>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {filteredItems.map((item) => (
                <Card key={item.id} className={`border-[#252A3A] ${item.status === 'rejected' ? 'bg-[#1a1212] opacity-80' : 'bg-[#141720]'}`}>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <CardTitle className="text-base capitalize text-white">{item.platform}</CardTitle>
                        <CardDescription>{item.title || 'Generated draft'}</CardDescription>
                      </div>
                      <Badge className={
                        item.status === 'rejected' ? 'border border-red-500/30 bg-red-500/15 text-red-300' :
                        item.degraded ? 'border border-amber-500/30 bg-amber-500/15 text-amber-300' :
                        'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300'
                      }>
                        {(item.status || item.generationStatus).replaceAll('_', ' ')}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="line-clamp-4 whitespace-pre-wrap text-sm text-slate-200">{cardBody(item)}</p>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <Badge className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">{item.format}</Badge>
                      <Badge className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">{item.providerActual || 'unknown'}</Badge>
                      <Badge className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">{item.modelActual || 'model unknown'}</Badge>
                      <Badge className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">fit {item.platformFitScore ?? 'n/a'}</Badge>
                    </div>
                    <div className="rounded-xl border border-[#252A3A] bg-[#0D0F14] p-3 text-xs text-slate-300 space-y-0.5">
                      <p>Business: {item.businessName || selectedBusiness?.name || 'unknown'}</p>
                      <p>Source: {item.sourceAction || 'unknown'}</p>
                      <p>Generated by: {item.generatedBy || item.providerActual || 'template'}</p>
                      <p>Media jobs: {item.mediaJobIds.length}</p>
                      <p>Assets: {item.mediaAssetIds.length || item.mediaUrls.length}</p>
                      <p>Asset status: {item.assetGenerationStatus || 'unknown'}</p>
                      {item.rejectionReason ? <p className="text-red-300">Rejection reason: {item.rejectionReason}</p> : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={async () => { await navigator.clipboard.writeText(cardBody(item)); toast.success('Copied content.'); }} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                        <Copy className="mr-1 h-3.5 w-3.5" />
                        Copy
                      </Button>
                      <Button size="sm" variant="outline" onClick={async () => { try { await contentApi.improveItem(item.id); await refreshItems(); toast.success('Improved draft created.'); } catch { toast.error('Improve failed.'); } }} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                        <Wand2 className="mr-1 h-3.5 w-3.5" />
                        Improve
                      </Button>
                      <Button size="sm" variant="outline" onClick={async () => { try { await contentApi.scheduleItem(item.id); await refreshItems(); toast.success('Item scheduled.'); } catch { toast.error('Schedule failed.'); } }} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                        <Calendar className="mr-1 h-3.5 w-3.5" />
                        Schedule
                      </Button>
                      <Button size="sm" variant="outline" onClick={async () => { try { await contentApi.duplicateItem(item.id); await refreshItems(); toast.success('Draft duplicated.'); } catch { toast.error('Duplicate failed.'); } }} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                        Duplicate
                      </Button>
                      {(item.status !== 'rejected') && (
                        <Button size="sm" variant="outline" onClick={() => { setRejectTarget(item.id); setRejectReason(''); }} className="border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20">
                          <XCircle className="mr-1 h-3.5 w-3.5" />
                          Reject
                        </Button>
                      )}
                      <Button size="sm" variant="outline" onClick={async () => { try { await contentApi.deleteItem(item.id); await refreshItems(); toast.success('Draft deleted.'); } catch { toast.error('Delete failed.'); } }} className="border-red-500/40 bg-red-500/10 text-red-200 hover:bg-red-500/20">
                        <Trash2 className="mr-1 h-3.5 w-3.5" />
                        Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Reject confirmation dialog */}
      {rejectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="w-full max-w-md rounded-2xl border border-[#252A3A] bg-[#0D0F14] p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-semibold text-white">Reject this draft?</h3>
            <p className="text-sm text-slate-400">
              It will be kept for learning and hidden from active drafts. You can view it under the "Rejected" filter.
            </p>
            <div className="space-y-2">
              <Label className="text-slate-300">What was wrong? (optional)</Label>
              <Textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Wrong hashtags, unrelated imagery, off-brand tone…"
                className="min-h-[80px] border-[#252A3A] bg-[#141720] text-white text-sm"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setRejectTarget(null)} className="border-[#252A3A] bg-transparent text-slate-300 hover:bg-white/5">
                Cancel
              </Button>
              <Button
                className="bg-amber-600 hover:bg-amber-500 text-white"
                onClick={async () => {
                  const id = rejectTarget;
                  setRejectTarget(null);
                  try {
                    await contentApi.rejectItem(id, { reason: rejectReason || undefined });
                    await refreshItems();
                    toast.success('Draft rejected and kept for learning.');
                  } catch {
                    toast.error('Rejection failed. The item was not changed.');
                  }
                }}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Confirm Reject
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
