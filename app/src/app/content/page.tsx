import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Calendar, Loader2, PenTool } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ContentStudio } from '@/components/dashboard/ContentStudio';
import { webAppApi } from '@/lib/api';
import type { WebApp } from '@/types';

export default function ContentPage() {
  const [searchParams] = useSearchParams();
  const initialBusinessId = searchParams.get('business') ?? undefined;
  const [businesses, setBusinesses] = useState<WebApp[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const loadedBusinesses = await webAppApi.getAll();
      setBusinesses(loadedBusinesses);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  // suppress unused variable lint warning
  void useMemo(() => null, []);

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
            Select a business, set your goal, choose what to create, pick platforms, and generate.
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
        />
      )}
    </div>
  );
}
