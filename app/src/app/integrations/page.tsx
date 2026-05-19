import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Cloud,
  ExternalLink,
  Instagram,
  Linkedin,
  Loader2,
  MessageSquare,
  Music,
  Pin,
  RefreshCw,
  Send,
  Twitter,
  Youtube,
  Facebook,
  AtSign,
  Camera,
} from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { getStoredToken } from '@/lib/auth';

interface ProviderKeyItem {
  key_name: string;
  label: string;
  provider: string;
  description: string;
  required: boolean;
  configured: boolean;
  masked: string;
  source: string;
  effective_configured: boolean;
  effective_source: string;
}

interface GlobalKeyItem {
  key_name: string;
  label: string;
  group: string;
  required: boolean;
  configured: boolean;
  masked: string;
  source: string;
}

interface APIKeysResponse {
  user_keys: ProviderKeyItem[];
  global_keys: GlobalKeyItem[];
}

interface PlatformIntegration {
  platform: string;
  is_connected: boolean;
  connected_at: string | null;
  platform_username: string | null;
  auto_post_enabled: boolean;
  auto_reply_enabled: boolean;
  low_risk_auto_reply: boolean;
}

interface ReadinessData {
  providers: Record<string, string>;
  provider_details: Record<string, { required: boolean; source: string; status: string; message?: string }>;
  checklist: { key: string; label: string; status: string; required: boolean }[];
  missing_required: string[];
  go_live_ready: boolean;
  genx?: {
    status: string;
    configured: boolean;
    health_ok: boolean;
    models_tested: boolean;
    required_models_ok: boolean;
    failed_models: { model: string; task: string; error?: string }[];
  };
  firecrawl?: {
    status: string;
    configured: boolean;
    error?: string | null;
  };
  social_platforms?: Record<string, { ui_status: string; can_post_now: boolean; missing: string[] }>;
}

const PLATFORMS = [
  { id: 'youtube', name: 'YouTube', icon: Youtube },
  { id: 'tiktok', name: 'TikTok', icon: Music },
  { id: 'instagram', name: 'Instagram', icon: Instagram },
  { id: 'facebook', name: 'Facebook', icon: Facebook },
  { id: 'twitter', name: 'Twitter / X', icon: Twitter },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin },
  { id: 'pinterest', name: 'Pinterest', icon: Pin },
  { id: 'reddit', name: 'Reddit', icon: MessageSquare },
  { id: 'bluesky', name: 'Bluesky', icon: Cloud },
  { id: 'threads', name: 'Threads', icon: AtSign },
  { id: 'telegram', name: 'Telegram', icon: Send },
  { id: 'snapchat', name: 'Snapchat', icon: Camera },
] as const;

const statusTone: Record<string, string> = {
  test_passed: 'bg-green-100 text-green-700 border-green-200',
  configured: 'bg-blue-100 text-blue-700 border-blue-200',
  test_failed: 'bg-red-100 text-red-700 border-red-200',
  missing: 'bg-amber-100 text-amber-800 border-amber-200',
  not_configured: 'bg-amber-100 text-amber-800 border-amber-200',
};

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function IntegrationsPage() {
  const [apiKeys, setApiKeys] = useState<APIKeysResponse>({ user_keys: [], global_keys: [] });
  const [integrations, setIntegrations] = useState<PlatformIntegration[]>([]);
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [testingKey, setTestingKey] = useState<string | null>(null);
  const [updatingPlatform, setUpdatingPlatform] = useState<string | null>(null);

  const globalKeyGroups = useMemo(() => {
    return apiKeys.global_keys.reduce<Record<string, GlobalKeyItem[]>>((acc, item) => {
      acc[item.group] = [...(acc[item.group] || []), item];
      return acc;
    }, {});
  }, [apiKeys.global_keys]);

  useEffect(() => {
    fetchData();

    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== 'amarktai-oauth-complete') return;
      toast.success(event.data.ok ? `${event.data.platform} connected` : `${event.data.platform} connection failed`);
      fetchData();
    };

    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const headers = authHeaders();
      const [keysRes, integrationsRes, readinessRes] = await Promise.all([
        fetch('/api/v1/settings/api-keys', { headers }),
        fetch('/api/v1/integrations/platforms', { headers }),
        fetch('/api/v1/settings/readiness', { headers }),
      ]);

      if (keysRes.ok) setApiKeys(await keysRes.json() as APIKeysResponse);
      if (integrationsRes.ok) setIntegrations(await integrationsRes.json() as PlatformIntegration[]);
      if (readinessRes.ok) setReadiness(await readinessRes.json() as ReadinessData);
    } catch {
      toast.error('Failed to load integrations');
    } finally {
      setIsLoading(false);
    }
  };

  const saveKey = async (keyName: string) => {
    const keyValue = (drafts[keyName] || '').trim();
    if (!keyValue) {
      toast.error('Enter a key value first');
      return;
    }

    setSavingKey(keyName);
    try {
      const res = await fetch('/api/v1/settings/api-keys', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ key_name: keyName, key_value: keyValue }),
      });
      if (!res.ok) throw new Error();
      setDrafts((prev) => ({ ...prev, [keyName]: '' }));
      toast.success('Provider key saved');
      await fetchData();
    } catch {
      toast.error('Failed to save key');
    } finally {
      setSavingKey(null);
    }
  };

  const testKey = async (keyName: string) => {
    setTestingKey(keyName);
    try {
      const keyValue = (drafts[keyName] || '').trim();
      const res = await fetch('/api/v1/settings/api-keys/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ key_name: keyName, key_value: keyValue || undefined }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Test failed');
      toast.success(`${keyName} test passed`);
      await fetchData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Test failed');
      await fetchData();
    } finally {
      setTestingKey(null);
    }
  };

  const testGenxModels = async () => {
    setTestingKey('GENX_MODELS');
    try {
      const res = await fetch('/api/v1/settings/genx/test-models', {
        method: 'POST',
        headers: authHeaders(),
      });
      const data = await res.json();
      if (!res.ok || !data.required_models_ok) throw new Error(data.failed_models?.[0]?.error || 'One or more required models failed');
      toast.success('GenX model tests passed');
      await fetchData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'GenX model test failed');
      await fetchData();
    } finally {
      setTestingKey(null);
    }
  };

  const testFirecrawl = async () => {
    setTestingKey('FIRECRAWL_CHECK');
    try {
      const res = await fetch('/api/v1/settings/firecrawl/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Firecrawl test failed');
      toast.success('Firecrawl test passed');
      await fetchData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Firecrawl test failed');
      await fetchData();
    } finally {
      setTestingKey(null);
    }
  };

  const handleConnectPlatform = async (platform: string) => {
    try {
      const res = await fetch(`/api/v1/integrations/platforms/${platform}/connect`, {
        headers: authHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to initiate connection');

      const width = 560;
      const height = 720;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      window.open(data.auth_url, 'Connect Platform', `width=${width},height=${height},left=${left},top=${top}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to initiate connection');
    }
  };

  const handleDisconnectPlatform = async (platform: string) => {
    setUpdatingPlatform(platform);
    try {
      const res = await fetch(`/api/v1/integrations/platforms/${platform}/disconnect`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error();
      toast.success(`${platform} disconnected`);
      await fetchData();
    } catch {
      toast.error('Failed to disconnect');
    } finally {
      setUpdatingPlatform(null);
    }
  };

  const handleUpdateIntegration = async (platform: string, updates: Partial<PlatformIntegration>) => {
    setUpdatingPlatform(platform);
    try {
      const res = await fetch(`/api/v1/integrations/platforms/${platform}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error();
      await fetchData();
    } catch {
      toast.error('Failed to update platform settings');
    } finally {
      setUpdatingPlatform(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Providers & Integrations</h2>
        <p className="text-gray-500">
          Add GenX and Firecrawl once here, then connect social platforms with OAuth.
        </p>
      </div>

      {readiness && (
        <Card className={readiness.go_live_ready ? 'border-green-200 bg-green-50/40' : 'border-amber-200 bg-amber-50/40'}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Go-live readiness
            </CardTitle>
            <CardDescription>
              GenX and Firecrawl are required. Social posting stays blocked until a valid OAuth connection exists.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {(['genx', 'firecrawl', 'qwen', 'huggingface', 'openai', 'gemini'] as const).map((provider) => {
                const detail = readiness.provider_details?.[provider];
                if (!detail) return null;
                return (
                  <div key={provider} className="rounded-lg border bg-white/80 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium capitalize">
                        {provider === 'huggingface' ? 'HuggingFace' : provider}
                        {detail.required ? ' (required)' : ' (optional)'}
                      </div>
                      <Badge className={statusTone[detail.status] || statusTone.configured}>{detail.status}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-gray-600">
                      Source: {detail.source === 'missing' ? 'not configured' : detail.source}
                    </p>
                    {detail.message && <p className="mt-1 text-xs text-red-600">{detail.message}</p>}
                  </div>
                );
              })}
            </div>

            <div className="flex flex-wrap gap-2 text-xs">
              {readiness.checklist.map((item) => (
                <Badge key={item.key} className={statusTone[item.status] || statusTone.configured}>
                  {item.label}: {item.status}
                </Badge>
              ))}
            </div>

            {!!readiness.missing_required.length && (
              <div className="text-sm text-amber-900">
                Missing required items: {readiness.missing_required.join(', ')}
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={testGenxModels}
                disabled={testingKey === 'GENX_MODELS'}
              >
                {testingKey === 'GENX_MODELS' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                Test GenX models
              </Button>
              <Button
                variant="outline"
                onClick={testFirecrawl}
                disabled={testingKey === 'FIRECRAWL_CHECK'}
              >
                {testingKey === 'FIRECRAWL_CHECK' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                Test Firecrawl
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Provider API keys</CardTitle>
          <CardDescription>
            This is the only dashboard place to save user-level provider keys.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {apiKeys.user_keys.map((item) => (
            <div key={item.key_name} className="rounded-lg border p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{item.label}</span>
                    <Badge className={statusTone[readiness?.provider_details?.[item.provider.toLowerCase()]?.status || (item.configured ? 'configured' : 'missing')] || statusTone.configured}>
                      {readiness?.provider_details?.[item.provider.toLowerCase()]?.status || (item.configured ? 'configured' : 'missing')}
                    </Badge>
                    <Badge variant="outline">{item.required ? 'Required' : 'Optional fallback'}</Badge>
                  </div>
                  <p className="text-sm text-gray-600">{item.description}</p>
                  <p className="text-xs text-gray-500">
                    Saved value: {item.masked || 'not saved'} • Effective source: {item.effective_source}
                  </p>
                </div>

                <div className="flex w-full max-w-2xl flex-col gap-3 lg:flex-row">
                  <div className="flex-1">
                    <Label htmlFor={item.key_name} className="sr-only">{item.label}</Label>
                    <Input
                      id={item.key_name}
                      value={drafts[item.key_name] || ''}
                      onChange={(event) => setDrafts((prev) => ({ ...prev, [item.key_name]: event.target.value }))}
                      placeholder={`Enter ${item.label}`}
                    />
                  </div>
                  <Button onClick={() => saveKey(item.key_name)} disabled={savingKey === item.key_name}>
                    {savingKey === item.key_name ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Save
                  </Button>
                  {(item.key_name === 'GENX_API_KEY' || item.key_name === 'FIRECRAWL_API_KEY') && (
                    <Button variant="outline" onClick={() => testKey(item.key_name)} disabled={testingKey === item.key_name}>
                      {testingKey === item.key_name ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                      Test
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Global runtime configuration</CardTitle>
          <CardDescription>
            These values come from the backend environment. They are shown separately from your encrypted user keys.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {Object.entries(globalKeyGroups).map(([group, items]) => (
            <div key={group} className="space-y-2">
              <h3 className="text-sm font-semibold">{group}</h3>
              <div className="grid gap-2 md:grid-cols-2">
                {items.map((item) => (
                  <div key={item.key_name} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium">{item.label}</span>
                      <Badge className={item.configured ? statusTone.configured : statusTone.missing}>
                        {item.configured ? 'configured' : 'not_configured'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-gray-600">{item.masked || 'not configured'}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Social platform OAuth</CardTitle>
          <CardDescription>
            Connect, reconnect, or disconnect platforms here. Posting stays blocked until the OAuth connection and required scopes are valid.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {PLATFORMS.map((platform) => {
            const Icon = platform.icon;
            const integration = integrations.find((item) => item.platform === platform.id);
            const posting = readiness?.social_platforms?.[platform.id];
            const canPost = posting?.can_post_now ?? false;
            const busy = updatingPlatform === platform.id;

            return (
              <div key={platform.id} className="rounded-lg border p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-100 p-2">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="font-medium">{platform.name}</div>
                      <div className="text-xs text-gray-500">
                        {integration?.platform_username || 'No account connected'}
                      </div>
                    </div>
                  </div>
                  <Badge className={canPost ? statusTone.test_passed : statusTone.missing}>
                    {posting?.ui_status || (integration?.is_connected ? 'Connected' : 'Needs connection')}
                  </Badge>
                </div>

                <div className="mt-3 space-y-2 text-xs text-gray-600">
                  <p>
                    OAuth env: {readiness?.oauth?.[platform.id] || 'not_configured'}
                  </p>
                  {posting?.missing?.length ? (
                    <p>Blocked by: {posting.missing.join(', ')}</p>
                  ) : (
                    <p>{canPost ? 'Posting is allowed for this platform.' : 'Posting is blocked until OAuth is valid.'}</p>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    onClick={() => handleConnectPlatform(platform.id)}
                    disabled={busy}
                  >
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ExternalLink className="mr-2 h-4 w-4" />}
                    {integration?.is_connected ? 'Reconnect' : 'Connect'}
                  </Button>
                  {integration?.is_connected && (
                    <Button size="sm" variant="outline" onClick={() => handleDisconnectPlatform(platform.id)} disabled={busy}>
                      Disconnect
                    </Button>
                  )}
                </div>

                {integration?.is_connected && (
                  <div className="mt-4 space-y-3 border-t pt-4">
                    <div className="flex items-center justify-between">
                      <Label htmlFor={`${platform.id}-autopost`}>Enable auto-post</Label>
                      <Switch
                        id={`${platform.id}-autopost`}
                        checked={integration.auto_post_enabled}
                        onCheckedChange={(checked) => handleUpdateIntegration(platform.id, { auto_post_enabled: checked })}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label htmlFor={`${platform.id}-autoreply`}>Enable auto-reply</Label>
                      <Switch
                        id={`${platform.id}-autoreply`}
                        checked={integration.auto_reply_enabled}
                        onCheckedChange={(checked) => handleUpdateIntegration(platform.id, { auto_reply_enabled: checked })}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>

      {readiness?.go_live_ready ? (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">
          <CheckCircle2 className="h-5 w-5" />
          Required providers are ready. Unsupported posting still remains blocked until each platform shows a valid posting status.
        </div>
      ) : null}
    </div>
  );
}
