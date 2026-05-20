import { useEffect, useMemo, useState } from 'react';
import {
  Facebook,
  Instagram,
  Linkedin,
  Loader2,
  MessageSquare,
  Music,
  Pin,
  RefreshCw,
  Twitter,
  Youtube,
  KeyRound,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface ProviderKeyItem {
  key_name: string;
  label: string;
  provider: string;
  description: string;
  required: boolean;
  configured: boolean;
}

interface APIKeysResponse {
  user_keys: ProviderKeyItem[];
}

interface PlatformIntegration {
  id: string;
  label: string;
  content_generation_available: boolean;
  oauth_supported: boolean;
  oauth_configured: boolean;
  user_connected: boolean;
  token_valid: boolean;
  scopes_ok: boolean;
  posting_supported: boolean;
  can_post_now: boolean;
  missing: string[];
  status_label: string;
  user_message: string;
}

interface ProviderDebugResult {
  ok?: boolean;
  status?: string;
  effective_source?: string;
  sanitized_preview?: string;
  endpoint?: string;
  base_url?: string;
  model?: string;
  http_status?: number;
  response_shape_keys?: string[];
  error?: string | null;
  [key: string]: unknown;
}

const requiredProviders = [
  { key: 'GENX_API_KEY', label: 'GenX key' },
  { key: 'FIRECRAWL_API_KEY', label: 'Firecrawl key' },
] as const;

const optionalProviders = [
  { key: 'QWEN_API_KEY', label: 'Qwen' },
  { key: 'HUGGINGFACE_TOKEN', label: 'HuggingFace' },
  { key: 'OPENAI_API_KEY', label: 'OpenAI' },
  { key: 'GEMINI_API_KEY', label: 'Gemini' },
] as const;

const socialPlatforms = [
  { id: 'instagram', label: 'Instagram', icon: Instagram },
  { id: 'facebook', label: 'Facebook', icon: Facebook },
  { id: 'linkedin', label: 'LinkedIn', icon: Linkedin },
  { id: 'twitter', label: 'X / Twitter', icon: Twitter },
  { id: 'tiktok', label: 'TikTok', icon: Music },
  { id: 'youtube', label: 'YouTube', icon: Youtube },
  { id: 'reddit', label: 'Reddit', icon: MessageSquare },
  { id: 'pinterest', label: 'Pinterest', icon: Pin },
] as const;

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('amarktai_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function providerBadge(status?: string) {
  if (status === 'test_passed') return 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300';
  if (status === 'test_failed') return 'border border-red-500/30 bg-red-500/15 text-red-300';
  return 'border border-amber-500/30 bg-amber-500/15 text-amber-300';
}

export default function IntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [apiKeys, setApiKeys] = useState<APIKeysResponse>({ user_keys: [] });
  const [integrations, setIntegrations] = useState<PlatformIntegration[]>([]);
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [testingKey, setTestingKey] = useState<string | null>(null);
  const [providerDebug, setProviderDebug] = useState<Record<string, ProviderDebugResult>>({});
  const [providerTests, setProviderTests] = useState<Record<string, ProviderDebugResult>>({});

  const load = async () => {
    try {
      setLoading(true);
      const [keysRes, integrationsRes, readinessRes] = await Promise.all([
        fetch('/api/v1/settings/api-keys', { headers: authHeaders() }),
        fetch('/api/v1/integrations/platforms', { headers: authHeaders() }),
        fetch('/api/v1/settings/readiness', { headers: authHeaders() }),
      ]);
      if (keysRes.ok) setApiKeys((await keysRes.json()) as APIKeysResponse);
      if (integrationsRes.ok) setIntegrations((await integrationsRes.json()) as PlatformIntegration[]);
      if (readinessRes.ok) setReadiness((await readinessRes.json()) as Record<string, unknown>);
    } catch {
      toast.error('Failed to load integrations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const savedKeys = useMemo(() => new Set(apiKeys.user_keys.filter((item) => item.configured).map((item) => item.key_name)), [apiKeys.user_keys]);
  const providerDetails = (readiness?.provider_details as Record<string, { status?: string; message?: string }> | undefined) ?? {};
  const socialReadiness = (readiness?.social_platforms as Record<string, { ui_status?: string; can_post_now?: boolean; missing?: string[] }> | undefined) ?? {};

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
      setDrafts((current) => ({ ...current, [keyName]: '' }));
      toast.success('Key saved');
      await load();
    } catch {
      toast.error('Failed to save key');
    } finally {
      setSavingKey(null);
    }
  };

  const testKey = async (keyName: string) => {
    setTestingKey(keyName);
    try {
      const res = await fetch('/api/v1/settings/api-keys/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ key_name: keyName, key_value: (drafts[keyName] || '').trim() || undefined }),
      });
      const data = await res.json();
      setProviderTests((current) => ({ ...current, [keyName]: data as ProviderDebugResult }));
      if (!res.ok || !data.ok) throw new Error(data.error || 'Test failed');
      toast.success('Provider test passed');
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Provider test failed');
      await load();
    } finally {
      setTestingKey(null);
    }
  };

  const debugProvider = async (keyName: string) => {
    setTestingKey(`debug-${keyName}`);
    try {
      const endpoint = keyName === 'GENX_API_KEY' ? '/api/v1/settings/genx/debug-test' : '/api/v1/settings/firecrawl/debug-test';
      const res = await fetch(endpoint, { method: 'POST', headers: authHeaders() });
      const data = (await res.json()) as ProviderDebugResult;
      setProviderDebug((current) => ({ ...current, [keyName]: data }));
      if (!res.ok || data.error) throw new Error(data.error || 'Debug failed');
      toast.success('Debug request complete');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Debug failed');
    } finally {
      setTestingKey(null);
    }
  };

  const testGenxModels = async () => {
    setTestingKey('GENX_MODELS');
    try {
      const res = await fetch('/api/v1/settings/genx/test-models', { method: 'POST', headers: authHeaders() });
      const data = await res.json();
      if (!res.ok || !data.required_models_ok) throw new Error(data.failed_models?.[0]?.error || 'GenX model test failed');
      toast.success('GenX model tests passed');
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'GenX model test failed');
      await load();
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
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Firecrawl test failed');
      await load();
    } finally {
      setTestingKey(null);
    }
  };

  const connectPlatform = async (platform: string) => {
    try {
      const res = await fetch(`/api/v1/integrations/platforms/${platform}/connect`, { headers: authHeaders() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Connection failed');
      window.open(data.auth_url, 'Connect Platform', 'width=560,height=720');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Connection failed');
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
      <div>
        <h1 className="text-2xl font-bold text-white">Integrations</h1>
        <p className="mt-2 text-sm text-slate-400">This is the only editable home for provider keys and social OAuth. Content generation stays available without social OAuth.</p>
      </div>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white"><KeyRound className="h-5 w-5 text-blue-300" />Required for generation</CardTitle>
          <CardDescription>GenX and Firecrawl power higher-quality generation and website analysis.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 xl:grid-cols-2">
          {requiredProviders.map((provider) => {
            const detail = provider.key === 'GENX_API_KEY' ? providerDetails.genx : providerDetails.firecrawl;
            return (
              <div key={provider.key} className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{provider.label}</p>
                    <p className="text-xs text-slate-400">{savedKeys.has(provider.key) ? 'saved' : 'missing'}</p>
                  </div>
                  <Badge className={providerBadge(detail?.status)}>{detail?.status || 'missing'}</Badge>
                </div>
                <div className="mt-4 space-y-2">
                  <Label className="text-slate-200">API key</Label>
                  <Input
                    type="password"
                    value={drafts[provider.key] || ''}
                    onChange={(event) => setDrafts((current) => ({ ...current, [provider.key]: event.target.value }))}
                    placeholder={savedKeys.has(provider.key) ? 'Saved — enter to replace' : 'Paste key'}
                    className="border-[#252A3A] bg-[#0D0F14] text-white"
                  />
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button onClick={() => saveKey(provider.key)} disabled={savingKey === provider.key} className="bg-blue-600 hover:bg-blue-500">
                    {savingKey === provider.key ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Save
                  </Button>
                  <Button variant="outline" onClick={() => testKey(provider.key)} disabled={testingKey === provider.key} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                    {testingKey === provider.key ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                    Test
                  </Button>
                  <Button variant="outline" onClick={() => debugProvider(provider.key)} disabled={testingKey === `debug-${provider.key}`} className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Debug
                  </Button>
                </div>
                {provider.key === 'GENX_API_KEY' ? (
                  <Button variant="outline" onClick={testGenxModels} disabled={testingKey === 'GENX_MODELS'} className="mt-3 border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                    {testingKey === 'GENX_MODELS' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                    Test GenX models
                  </Button>
                ) : (
                  <Button variant="outline" onClick={testFirecrawl} disabled={testingKey === 'FIRECRAWL_CHECK'} className="mt-3 border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                    {testingKey === 'FIRECRAWL_CHECK' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                    Test Firecrawl
                  </Button>
                )}
                <p className="mt-3 text-xs text-slate-400">Last status: {detail?.message || detail?.status || 'missing'}</p>
                {providerDebug[provider.key]?.sanitized_preview ? (
                  <div className="mt-3 rounded-xl border border-[#252A3A] bg-[#0D0F14] p-3 text-xs text-slate-300">
                    Debug preview: {providerDebug[provider.key]?.sanitized_preview}
                  </div>
                ) : null}
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle className="text-white">Optional fallback AI providers</CardTitle>
          <CardDescription>Use these only as fallbacks when required providers are missing or degraded.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {optionalProviders.map((provider) => (
            <div key={provider.key} className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-white">{provider.label}</p>
                <Badge className={savedKeys.has(provider.key) ? 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300' : 'border border-[#252A3A] bg-[#0D0F14] text-slate-300'}>
                  {savedKeys.has(provider.key) ? 'saved' : 'optional'}
                </Badge>
              </div>
              <div className="mt-4 space-y-2">
                <Label className="text-slate-200">API key</Label>
                <Input
                  type="password"
                  value={drafts[provider.key] || ''}
                  onChange={(event) => setDrafts((current) => ({ ...current, [provider.key]: event.target.value }))}
                  placeholder={savedKeys.has(provider.key) ? 'Saved — enter to replace' : 'Paste key'}
                  className="border-[#252A3A] bg-[#0D0F14] text-white"
                />
              </div>
              <Button onClick={() => saveKey(provider.key)} disabled={savingKey === provider.key} className="mt-4 w-full bg-blue-600 hover:bg-blue-500">
                {savingKey === provider.key ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Save
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle className="text-white">Social posting connections</CardTitle>
          <CardDescription>Generation is always available. OAuth only unlocks posting readiness.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 xl:grid-cols-2">
          {socialPlatforms.map((platform) => {
            const Icon = platform.icon;
            const integration = integrations.find((item) => item.id === platform.id);
            const state = socialReadiness[platform.id] || {};
            const missing = integration?.missing ?? ((state.missing as string[] | undefined) ?? []);
            const canConnect = Boolean(integration?.oauth_supported && integration?.oauth_configured && integration?.posting_supported);
            const connectLabel = !integration?.oauth_configured
              ? 'Configure OAuth app first'
              : !integration?.posting_supported
                ? 'Posting not implemented'
                : 'Connect OAuth';
            return (
              <div key={platform.id} className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-xl bg-[#0D0F14] p-2 text-blue-300"><Icon className="h-5 w-5" /></div>
                    <div>
                      <p className="font-medium text-white">{platform.label}</p>
                      <p className="text-xs text-slate-400">Content generation available</p>
                    </div>
                  </div>
                  <Badge className={integration?.can_post_now ? 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300' : 'border border-amber-500/30 bg-amber-500/15 text-amber-300'}>
                    {integration?.status_label || String(state.ui_status || 'Limited mode')}
                  </Badge>
                </div>
                <div className="mt-4 rounded-xl border border-[#252A3A] bg-[#0D0F14] p-3 text-sm text-slate-300">
                  <p>Posting: {integration?.user_connected ? 'OAuth connected' : 'Posting not configured'}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {integration?.user_message || 'OAuth connection required only when you want to post.'}
                  </p>
                </div>
                {missing.length > 0 ? (
                  <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
                    <div className="flex items-center gap-2 font-medium"><AlertCircle className="h-4 w-4" />Missing requirements</div>
                    <p className="mt-2">{missing.join(', ')}</p>
                  </div>
                ) : null}
                <div className="mt-4 flex gap-3">
                  <Button
                    onClick={() => connectPlatform(platform.id)}
                    disabled={!canConnect}
                    className={canConnect ? 'bg-blue-600 hover:bg-blue-500' : 'bg-slate-700 text-slate-300 hover:bg-slate-700'}
                  >
                    {connectLabel}
                  </Button>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle className="text-white">Last provider test results</CardTitle>
          <CardDescription>Save, test, and debug results are shown here with actionable details.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 xl:grid-cols-2">
          {requiredProviders.map((provider) => {
            const testResult = providerTests[provider.key];
            const debugResult = providerDebug[provider.key];
            return (
              <div key={`result-${provider.key}`} className="rounded-2xl border border-[#252A3A] bg-[#141720] p-4">
                <p className="font-medium text-white">{provider.label}</p>
                <div className="mt-3 space-y-2 text-xs text-slate-300">
                  <p><span className="text-slate-400">Test:</span> {testResult ? JSON.stringify(testResult) : 'No test run yet.'}</p>
                  <p><span className="text-slate-400">Debug:</span> {debugResult ? JSON.stringify(debugResult) : 'No debug run yet.'}</p>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
