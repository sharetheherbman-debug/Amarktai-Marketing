import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertTriangle, CalendarClock, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import {
  addDays,
  addMonths,
  addWeeks,
  endOfMonth,
  endOfWeek,
  eachDayOfInterval,
  format,
  startOfDay,
  startOfMonth,
  startOfWeek,
  subDays,
  subMonths,
  subWeeks,
} from 'date-fns';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { getStoredToken } from '@/lib/auth';
import { PLATFORM_CATALOG } from '@/lib/platformCatalog';
import { webAppApi } from '@/lib/api';
import type { WebApp } from '@/types';

type SchedulerView = 'month' | 'week' | 'day' | 'list';

interface SchedulerItem {
  id: string;
  business_id: string;
  content_id: string;
  platform: string;
  platform_label: string;
  title: string;
  planned_at: string | null;
  status: string;
  posting_readiness: string;
  mode: string;
  notes?: string | null;
  metadata?: Record<string, unknown>;
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function SchedulerPage() {
  const [searchParams] = useSearchParams();
  const [view, setView] = useState<SchedulerView>('month');
  const [cursor, setCursor] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<SchedulerItem[]>([]);
  const [businesses, setBusinesses] = useState<WebApp[]>([]);
  const [businessFilter, setBusinessFilter] = useState(searchParams.get('business') ?? 'all');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workerMessage, setWorkerMessage] = useState('Manual scheduling/planning active. Automatic publishing worker not configured.');
  const [savingId, setSavingId] = useState<string | null>(null);

  const range = useMemo(() => {
    if (view === 'month') return { start: startOfMonth(cursor), end: endOfMonth(cursor) };
    if (view === 'week') return { start: startOfWeek(cursor), end: endOfWeek(cursor) };
    if (view === 'day') return { start: startOfDay(cursor), end: startOfDay(cursor) };
    return { start: startOfMonth(cursor), end: endOfMonth(cursor) };
  }, [cursor, view]);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [calendarRes, businessesRes, workerRes] = await Promise.all([
        fetch(`/api/v1/scheduler/calendar?start=${encodeURIComponent(range.start.toISOString())}&end=${encodeURIComponent(range.end.toISOString())}`, { headers: authHeaders() }),
        webAppApi.getAll(),
        fetch('/api/v1/workers/status', { headers: authHeaders() }),
      ]);
      if (!calendarRes.ok) throw new Error(`Scheduler API ${calendarRes.status}`);
      const calendarData = await calendarRes.json() as { items?: SchedulerItem[] };
      setItems(Array.isArray(calendarData.items) ? calendarData.items : []);
      setBusinesses(businessesRes);
      if (workerRes.ok) {
        const workerData = await workerRes.json() as { message?: string };
        setWorkerMessage(workerData.message || workerMessage);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scheduler');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [view, cursor]);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      if (businessFilter !== 'all' && item.business_id !== businessFilter) return false;
      if (platformFilter !== 'all' && item.platform !== platformFilter) return false;
      if (statusFilter !== 'all' && item.status !== statusFilter) return false;
      return true;
    });
  }, [businessFilter, items, platformFilter, statusFilter]);

  const selectedItem = filtered.find((item) => item.id === selectedId) ?? filtered[0] ?? null;

  const calendarDays = useMemo(() => eachDayOfInterval({ start: range.start, end: range.end }), [range]);

  const moveCursor = (direction: -1 | 1) => {
    setCursor((current) => {
      if (view === 'month') return direction === 1 ? addMonths(current, 1) : subMonths(current, 1);
      if (view === 'week') return direction === 1 ? addWeeks(current, 1) : subWeeks(current, 1);
      return direction === 1 ? addDays(current, 1) : subDays(current, 1);
    });
  };

  const updateSchedule = async (item: SchedulerItem, plannedAt: string) => {
    try {
      setSavingId(item.id);
      const res = await fetch(`/api/v1/scheduler/items/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ planned_at: new Date(plannedAt).toISOString() }),
      });
      if (!res.ok) throw new Error(`Update failed ${res.status}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reschedule');
    } finally {
      setSavingId(null);
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
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Scheduler</h2>
          <p className="text-slate-400">Real planning calendar backed by persisted scheduler items.</p>
        </div>
        <div className="flex gap-2">
          {(['month', 'week', 'day', 'list'] as SchedulerView[]).map((nextView) => (
            <Button
              key={nextView}
              variant="outline"
              onClick={() => setView(nextView)}
              className={view === nextView ? 'border-blue-500/40 bg-blue-500/10 text-blue-200' : 'border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5'}
            >
              {nextView}
            </Button>
          ))}
        </div>
      </div>

      <Card className="border-amber-500/30 bg-amber-500/10">
        <CardContent className="p-4 text-amber-100">
          <div className="flex items-center gap-2 font-medium">
            <AlertTriangle className="h-4 w-4" />
            {workerMessage}
          </div>
        </CardContent>
      </Card>

      {error ? (
        <Card className="border-red-500/30 bg-red-500/10">
          <CardContent className="p-4 text-red-200">{error}</CardContent>
        </Card>
      ) : null}

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-white">
                <CalendarClock className="h-5 w-5 text-blue-300" />
                Calendar
              </CardTitle>
              <CardDescription>Statuses: draft, scheduled, posted, failed, manual review.</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => moveCursor(-1)} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="min-w-[180px] text-center text-sm text-slate-200">{format(cursor, view === 'month' ? 'MMMM yyyy' : 'PPP')}</span>
              <Button variant="outline" onClick={() => moveCursor(1)} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
            <select value={businessFilter} onChange={(event) => setBusinessFilter(event.target.value)} className="rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2 text-sm text-white">
              <option value="all">All businesses</option>
              {businesses.map((business) => <option key={business.id} value={business.id}>{business.name}</option>)}
            </select>
            <select value={platformFilter} onChange={(event) => setPlatformFilter(event.target.value)} className="rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2 text-sm text-white">
              <option value="all">All platforms</option>
              {PLATFORM_CATALOG.map((platform) => <option key={platform.id} value={platform.id}>{platform.label}</option>)}
            </select>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-xl border border-[#252A3A] bg-[#141720] px-3 py-2 text-sm text-white">
              <option value="all">All statuses</option>
              {['draft', 'scheduled', 'posted', 'failed', 'manual_review'].map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </div>

          {view === 'list' ? (
            <div className="space-y-3">
              {filtered.map((item) => (
                <div key={item.id} className="rounded-xl border border-[#252A3A] bg-[#141720] p-4" onClick={() => setSelectedId(item.id)}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-white">{item.title}</p>
                      <p className="text-xs text-slate-400">{item.platform_label} · {item.planned_at ? format(new Date(item.planned_at), 'PPP p') : 'Unscheduled'}</p>
                    </div>
                    <Badge className="border border-[#252A3A] bg-[#0D0F14] text-slate-200">{item.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={`grid gap-3 ${view === 'month' ? 'md:grid-cols-7' : view === 'week' ? 'md:grid-cols-7' : 'md:grid-cols-1'}`}>
              {calendarDays.map((day) => {
                const dayItems = filtered.filter((item) => item.planned_at && format(new Date(item.planned_at), 'yyyy-MM-dd') === format(day, 'yyyy-MM-dd'));
                return (
                  <div key={day.toISOString()} className="rounded-xl border border-[#252A3A] bg-[#141720] p-3">
                    <p className="text-sm font-medium text-white">{format(day, 'EEE d')}</p>
                    <div className="mt-3 space-y-2">
                      {dayItems.length === 0 ? <p className="text-xs text-slate-500">No scheduled items</p> : null}
                      {dayItems.map((item) => (
                        <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className="block w-full rounded-lg border border-[#252A3A] bg-[#0D0F14] p-2 text-left">
                          <p className="truncate text-xs font-medium text-white">{item.title}</p>
                          <p className="text-[11px] text-slate-400">{item.platform_label}</p>
                          <p className="text-[11px] text-slate-500">{item.planned_at ? format(new Date(item.planned_at), 'p') : 'No time'}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedItem ? (
        <Card className="border-[#252A3A] bg-[#0D0F14]">
          <CardHeader>
            <CardTitle className="text-white">Selected content</CardTitle>
            <CardDescription>Preview and reschedule this real planner item.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="font-medium text-white">{selectedItem.title}</p>
            <div className="flex flex-wrap gap-2">
              <Badge className="border border-[#252A3A] bg-[#141720] text-slate-200">{selectedItem.platform_label}</Badge>
              <Badge className="border border-[#252A3A] bg-[#141720] text-slate-200">{selectedItem.status}</Badge>
              <Badge className="border border-[#252A3A] bg-[#141720] text-slate-200">{selectedItem.posting_readiness}</Badge>
              <Badge className="border border-[#252A3A] bg-[#141720] text-slate-200">{selectedItem.mode}</Badge>
            </div>
            <Input
              type="datetime-local"
              defaultValue={selectedItem.planned_at ? format(new Date(selectedItem.planned_at), "yyyy-MM-dd'T'HH:mm") : ''}
              onBlur={(event) => {
                if (event.target.value) {
                  void updateSchedule(selectedItem, event.target.value);
                }
              }}
              className="border-[#252A3A] bg-[#141720] text-white"
            />
            {savingId === selectedItem.id ? <p className="text-xs text-slate-400">Saving…</p> : null}
            {selectedItem.metadata?.user_message ? <p className="text-sm text-slate-300">{String(selectedItem.metadata.user_message)}</p> : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
