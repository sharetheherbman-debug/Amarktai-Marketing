import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowRight, Building2, Globe, Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { webAppApi } from '@/lib/api';
import type { WebApp } from '@/types';

function scrapeBadge(webapp: WebApp) {
  const scraped = (webapp.scrapedData as Record<string, unknown> | null | undefined) ?? null;
  const status = String(scraped?.scrape_status || 'not_started');
  if (status === 'success') return { label: 'Analyzed', className: 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300' };
  if (status === 'partial') return { label: 'Warnings', className: 'border border-amber-500/30 bg-amber-500/15 text-amber-300' };
  if (status === 'failed') return { label: 'Needs review', className: 'border border-amber-500/30 bg-amber-500/15 text-amber-300' };
  return { label: 'Not analyzed', className: 'border border-slate-600 bg-slate-800 text-slate-300' };
}

export default function BusinessListPage() {
  const [businesses, setBusinesses] = useState<WebApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const loadBusinesses = async () => {
    try {
      const items = await webAppApi.getAll();
      setBusinesses(items);
    } catch {
      toast.error('Failed to load businesses');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadBusinesses();
  }, []);

  const handleRefresh = async (business: WebApp) => {
    setRefreshingId(business.id);
    try {
      const result = await webAppApi.refreshIntelligence(business.id);
      const warnings = (result.intelligence?.warnings as string[] | undefined) ?? [];
      toast.success(warnings.length > 0 ? 'Business refreshed with warnings.' : 'Business analysis refreshed.');
      await loadBusinesses();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Business analysis failed');
    } finally {
      setRefreshingId(null);
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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Businesses</h1>
          <p className="mt-2 text-sm text-slate-400">Every business profile feeds website analysis and content generation.</p>
        </div>
        <Link to="/dashboard/businesses/new">
          <Button className="bg-blue-600 hover:bg-blue-500">
            <Plus className="mr-2 h-4 w-4" />
            Add Business
          </Button>
        </Link>
      </div>

      {businesses.length === 0 ? (
        <Card className="border-dashed border-blue-500/30 bg-[#0D0F14]">
          <CardContent className="flex flex-col items-start gap-4 p-8">
            <div className="rounded-2xl bg-blue-500/15 p-3 text-blue-300">
              <Building2 className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Add your first business to start generating content</h2>
              <p className="mt-2 text-sm text-slate-400">You can use a business name, website URL, or both.</p>
            </div>
            <Link to="/dashboard/businesses/new">
              <Button className="bg-blue-600 hover:bg-blue-500">Add Business</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {businesses.map((business) => {
            const status = scrapeBadge(business);
            const warnings = (((business.scrapedData as Record<string, unknown> | null | undefined)?.warnings) as string[] | undefined) ?? [];
            return (
              <Card key={business.id} className="border-[#252A3A] bg-[#0D0F14]">
                <CardHeader>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="flex items-center gap-2 text-white">
                        <Building2 className="h-5 w-5 text-blue-300" />
                        {business.name || 'Business profile'}
                      </CardTitle>
                      <CardDescription className="mt-2 text-slate-400">
                        {business.url || 'No website URL yet'}
                      </CardDescription>
                    </div>
                    <Badge className={status.className}>{status.label}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-slate-300">{business.description || 'No description yet. Add notes or analyze the website to enrich this profile.'}</p>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-500">Category</p>
                      <p className="mt-2 text-sm text-white">{business.category || 'Not set'}</p>
                    </div>
                    <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-500">Target audience</p>
                      <p className="mt-2 text-sm text-white">{business.targetAudience || 'Needs review'}</p>
                    </div>
                  </div>

                  {warnings.length > 0 ? (
                    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
                      <div className="flex items-center gap-2 font-medium">
                        <AlertCircle className="h-4 w-4" />
                        Website analysis warnings
                      </div>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
                        {warnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div className="flex flex-wrap gap-3">
                    <Button
                      variant="outline"
                      onClick={() => handleRefresh(business)}
                      disabled={refreshingId === business.id}
                      className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5"
                    >
                      {refreshingId === business.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Globe className="mr-2 h-4 w-4" />}
                      Analyze Website
                    </Button>
                    <Link to={`/dashboard/businesses/${business.id}`}>
                      <Button className="bg-blue-600 hover:bg-blue-500">
                        Open Business
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Button>
                    </Link>
                    <Link to={`/dashboard/content?business=${business.id}`}>
                      <Button variant="outline" className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                        Generate Content
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
