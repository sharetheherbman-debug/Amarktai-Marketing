import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Bell, Building2, ExternalLink, Loader2, Settings2, Shield, User } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useAuth } from '@/lib/auth';
import { settingsApi } from '@/lib/api';

interface SettingsData {
  timezone: string;
  language: string;
  notification_email: boolean;
  notification_digest: boolean;
}

function statusBadge(status?: string) {
  if (status === 'test_passed') return 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300';
  if (status === 'test_failed') return 'border border-red-500/30 bg-red-500/15 text-red-300';
  return 'border border-amber-500/30 bg-amber-500/15 text-amber-300';
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [savingNotifications, setSavingNotifications] = useState(false);
  const [savingWorkspace, setSavingWorkspace] = useState(false);
  const [workspace, setWorkspace] = useState({ timezone: 'UTC', language: 'en' });
  const [notifications, setNotifications] = useState({ emailDaily: true, emailWeekly: true });
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [providerResolution, setProviderResolution] = useState<Record<string, unknown> | null>(null);

  const authHeaders = useCallback(() => {
    const token = localStorage.getItem('amarktai_token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }, []);

  const load = useCallback(async () => {
    try {
      const tokenHeaders = authHeaders();
      const [settingsRes, readinessData, providerData] = await Promise.all([
        fetch('/api/v1/settings', { headers: tokenHeaders }),
        settingsApi.getReadiness(),
        settingsApi.getProviderResolution(),
      ]);
      if (settingsRes.ok) {
        const settingsData = (await settingsRes.json()) as SettingsData;
        setWorkspace({ timezone: settingsData.timezone || 'UTC', language: settingsData.language || 'en' });
        setNotifications({
          emailDaily: settingsData.notification_email ?? true,
          emailWeekly: settingsData.notification_digest ?? true,
        });
      }
      setReadiness(readinessData);
      setProviderResolution(providerData);
    } catch {
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, [authHeaders]);

  useEffect(() => {
    void load();
  }, [load]);

  const saveNotifications = async () => {
    setSavingNotifications(true);
    try {
      const res = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          notification_email: notifications.emailDaily,
          notification_digest: notifications.emailWeekly,
        }),
      });
      if (!res.ok) throw new Error();
      toast.success('Notification preferences saved');
    } catch {
      toast.error('Failed to save notifications');
    } finally {
      setSavingNotifications(false);
    }
  };

  const saveWorkspace = async () => {
    setSavingWorkspace(true);
    try {
      const res = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ timezone: workspace.timezone, language: workspace.language }),
      });
      if (!res.ok) throw new Error();
      toast.success('Workspace defaults saved');
    } catch {
      toast.error('Failed to save workspace defaults');
    } finally {
      setSavingWorkspace(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
      </div>
    );
  }

  const providerDetails = (readiness?.provider_details as Record<string, { status?: string }> | undefined) ?? {};
  const providers = (providerResolution?.providers as Record<string, { effective_source?: string }> | undefined) ?? {};

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="mt-2 text-sm text-slate-400">Minimal workspace settings only. Provider keys and social connections are managed in Integrations.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-[#252A3A] bg-[#0D0F14]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white"><User className="h-5 w-5 text-blue-300" />Account</CardTitle>
            <CardDescription>Read-only account summary.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Name</p>
              <p className="mt-2 text-white">{user?.name || 'Account user'}</p>
            </div>
            <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Email</p>
              <p className="mt-2 text-white">{user?.email || 'No email available'}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#252A3A] bg-[#0D0F14]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white"><Building2 className="h-5 w-5 text-blue-300" />Workspace / business defaults</CardTitle>
            <CardDescription>Preferences that shape the workspace, not provider credentials.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-slate-200">Timezone</Label>
                <Input value={workspace.timezone} onChange={(event) => setWorkspace((current) => ({ ...current, timezone: event.target.value }))} className="border-[#252A3A] bg-[#141720] text-white" />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-200">Language</Label>
                <Input value={workspace.language} onChange={(event) => setWorkspace((current) => ({ ...current, language: event.target.value }))} className="border-[#252A3A] bg-[#141720] text-white" />
              </div>
            </div>
            <Button onClick={saveWorkspace} disabled={savingWorkspace} className="bg-blue-600 hover:bg-blue-500">
              {savingWorkspace ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Save workspace defaults
            </Button>
          </CardContent>
        </Card>

        <Card className="border-[#252A3A] bg-[#0D0F14] lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white"><Settings2 className="h-5 w-5 text-blue-300" />Runtime status</CardTitle>
            <CardDescription>Provider keys are managed in Integrations.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-xl border border-[#252A3A] bg-[#141720] p-4 text-sm text-slate-300">
              Provider Keys are managed in Integrations.
              <Link to="/dashboard/integrations" className="ml-2 inline-flex items-center gap-1 font-medium text-blue-300">
                Open Integrations
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              {[
                { label: 'GenX', status: providerDetails.genx?.status, source: providers.GENX_API_KEY?.effective_source },
                { label: 'Firecrawl', status: providerDetails.firecrawl?.status, source: providers.FIRECRAWL_API_KEY?.effective_source },
                { label: 'Fallback providers', status: 'optional', source: [providers.QWEN_API_KEY?.effective_source, providers.HUGGINGFACE_TOKEN?.effective_source, providers.OPENAI_API_KEY?.effective_source, providers.GEMINI_API_KEY?.effective_source].filter(Boolean).join(', ') || 'Not configured' },
              ].map((item) => (
                <div key={item.label} className="rounded-xl border border-[#252A3A] bg-[#141720] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-white">{item.label}</p>
                    <Badge className={item.status === 'optional' ? 'border border-[#252A3A] bg-[#0D0F14] text-slate-200' : statusBadge(item.status)}>
                      {item.status === 'optional' ? 'optional' : (item.status || 'missing')}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-slate-400">Source: {item.source || 'missing'}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#252A3A] bg-[#0D0F14]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white"><Bell className="h-5 w-5 text-blue-300" />Notifications</CardTitle>
            <CardDescription>Simple notification preferences.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-xl border border-[#252A3A] bg-[#141720] p-4">
              <div>
                <p className="font-medium text-white">Email when content is ready</p>
                <p className="text-sm text-slate-400">Daily generation updates.</p>
              </div>
              <Switch checked={notifications.emailDaily} onCheckedChange={(value) => setNotifications((current) => ({ ...current, emailDaily: value }))} />
            </div>
            <div className="flex items-center justify-between rounded-xl border border-[#252A3A] bg-[#141720] p-4">
              <div>
                <p className="font-medium text-white">Weekly digest</p>
                <p className="text-sm text-slate-400">Summary of engagement and content output.</p>
              </div>
              <Switch checked={notifications.emailWeekly} onCheckedChange={(value) => setNotifications((current) => ({ ...current, emailWeekly: value }))} />
            </div>
            <Button onClick={saveNotifications} disabled={savingNotifications} className="bg-blue-600 hover:bg-blue-500">
              {savingNotifications ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Save notification settings
            </Button>
          </CardContent>
        </Card>

        <Card className="border-[#252A3A] bg-[#0D0F14]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white"><Shield className="h-5 w-5 text-blue-300" />Danger zone</CardTitle>
            <CardDescription>Status only. No fake destructive actions.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
              <div className="flex items-center gap-2 font-medium">
                <AlertTriangle className="h-4 w-4" />
                Workspace deletion is not available from this beta settings screen.
              </div>
              <p className="mt-2 text-red-100/80">Use support or admin workflows for destructive actions until the product flow is hardened.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
