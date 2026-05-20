import { useEffect, useState } from 'react';
import { CalendarClock, Loader2, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getStoredToken } from '@/lib/auth';

interface ScheduledItem {
  id: string;
  platform: string;
  title: string;
  scheduled_for: string | null;
  status: string;
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function SchedulerPage() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<ScheduledItem[]>([]);
  const [workerConfigured, setWorkerConfigured] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [upcomingRes, readinessRes] = await Promise.all([
          fetch('/api/v1/scheduler/upcoming', { headers: authHeaders() }),
          fetch('/api/v1/settings/readiness', { headers: authHeaders() }),
        ]);
        if (!upcomingRes.ok) throw new Error(`Scheduler API ${upcomingRes.status}`);
        const upcoming = await upcomingRes.json() as { items?: ScheduledItem[] };
        setItems(Array.isArray(upcoming.items) ? upcoming.items : []);

        if (readinessRes.ok) {
          const readiness = await readinessRes.json() as { providers?: { scheduler_celery?: string } };
          setWorkerConfigured((readiness.providers?.scheduler_celery || '') === 'configured');
        } else {
          setWorkerConfigured(false);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load scheduler');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Scheduler</h2>
        <p className="text-slate-400">Plan and review scheduled content with truthful live status.</p>
      </div>

      {!workerConfigured ? (
        <Card className="border-amber-500/30 bg-amber-500/10">
          <CardContent className="p-4 text-amber-100">
            <div className="flex items-center gap-2 font-medium">
              <AlertTriangle className="h-4 w-4" />
              Automatic publishing is not configured. You can still plan and review scheduled content.
            </div>
          </CardContent>
        </Card>
      ) : null}

      {error ? (
        <Card className="border-red-500/30 bg-red-500/10">
          <CardContent className="p-4 text-red-200">{error}</CardContent>
        </Card>
      ) : null}

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <CalendarClock className="h-5 w-5 text-blue-300" />
            Scheduled content
          </CardTitle>
          <CardDescription>Upcoming scheduled posts from your workspace.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[#252A3A] bg-[#141720] p-5 text-sm text-slate-300">
              No scheduled posts yet. Generate content first, then schedule it.
            </div>
          ) : (
            items.map((item) => (
              <div key={item.id} className="rounded-xl border border-[#252A3A] bg-[#141720] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-white">{item.title || 'Untitled'}</p>
                  <Badge className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">{item.status}</Badge>
                </div>
                <p className="mt-1 text-sm capitalize text-slate-300">{item.platform}</p>
                <p className="mt-1 text-xs text-slate-400">{item.scheduled_for || 'Not scheduled yet'}</p>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
