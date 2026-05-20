import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Calendar, Loader2, PenTool } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ContentStudio } from '@/components/dashboard/ContentStudio';
import { contentApi, webAppApi } from '@/lib/api';
import type { Content, WebApp } from '@/types';

export default function ContentPage() {
  const [searchParams] = useSearchParams();
  const initialBusinessId = searchParams.get('business') ?? undefined;
  const [businesses, setBusinesses] = useState<WebApp[]>([]);
  const [content, setContent] = useState<Content[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [loadedBusinesses, loadedContent] = await Promise.all([
        webAppApi.getAll(),
        contentApi.getAll(),
      ]);
      setBusinesses(loadedBusinesses);
      setContent(loadedContent);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const library = useMemo(() => content.slice(0, 8), [content]);

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
          <h1 className="text-2xl font-bold text-white">Content Studio</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Select a real business profile, choose a platform, set the objective and tone, then generate content. No hidden setup or fake default business IDs.
          </p>
        </div>
        <Link to="/dashboard/scheduler">
          <Button variant="outline" className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
            <Calendar className="mr-2 h-4 w-4" />
            Open Scheduler
          </Button>
        </Link>
      </div>

      {businesses.length === 0 ? (
        <Card className="border-dashed border-blue-500/30 bg-[#0D0F14]">
          <CardContent className="flex flex-col items-start gap-4 p-8">
            <div className="rounded-2xl bg-blue-500/15 p-3 text-blue-300">
              <PenTool className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Add Business</h2>
              <p className="mt-2 text-sm text-slate-400">Content Studio stays empty until a real business profile exists.</p>
            </div>
            <Link to="/dashboard/businesses/new">
              <Button className="bg-blue-600 hover:bg-blue-500">Add Business</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <ContentStudio
          initialBusinessId={initialBusinessId}
          onGenerated={(items) => setContent((current) => [...items, ...current])}
        />
      )}

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle>Recent generated content</CardTitle>
          <CardDescription>Newest drafts across all businesses.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {library.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[#252A3A] bg-[#141720] p-4 text-sm text-slate-400">
              No generated content yet. Choose a business and generate your first campaign.
            </div>
          ) : (
            library.map((item) => {
              const metadata = (item.generationMetadata as Record<string, unknown> | undefined) ?? {};
              return (
                <div key={item.id} className="rounded-xl border border-[#252A3A] bg-[#141720] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium capitalize text-white">{item.platform}</p>
                      <p className="text-xs text-slate-400">{item.status}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">{String(metadata.scrape_status || 'unknown')}</Badge>
                      <Badge className={metadata.degraded === true ? 'border border-amber-500/30 bg-amber-500/15 text-amber-300' : 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300'}>
                        {metadata.degraded === true ? 'Degraded' : 'Ready'}
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-3 line-clamp-3 text-sm text-slate-300">{item.caption}</p>
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </div>
  );
}
