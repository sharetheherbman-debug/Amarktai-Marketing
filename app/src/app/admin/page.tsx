/**
 * Admin Panel – System Configuration
 *
 * Allows the administrator to:
 * - Set system-level API keys (AI engine, social platforms, etc.)
 * - Toggle feature flags
 * - View live system health stats
 * - Trigger manual content generation
 *
 * Designed and created by AmarktAI Marketing
 */

import { useEffect, useState } from 'react';
import {
  ShieldCheck, Key, Zap, RefreshCw, Users, FileText,
  CheckCircle2, XCircle, Eye, EyeOff, Play, Settings2,
  BarChart3, AlertTriangle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { getStoredToken } from '@/lib/auth';

// ─── Types ───────────────────────────────────────────────────────────────────

interface SystemHealth {
  status: string;
  timestamp: string;
  stats: {
    total_users: number;
    total_webapps: number;
    total_content: number;
    pending_content: number;
    posted_content: number;
  };
  configured_system_keys: string[];
  feature_flags: {
    enable_auto_post: boolean;
    enable_auto_reply: boolean;
    enable_ab_testing: boolean;
    enable_viral_prediction: boolean;
    enable_cost_tracking: boolean;
    max_content_per_day: number;
  };
}

interface SystemKeys {
  keys: Record<string, string>;
}

const KEY_GROUPS: { label: string; keys: string[] }[] = [
  {
    label: 'AI Engine / LLM',
    keys: [
      'GENX_API_KEY',
      'QWEN_API_KEY',
      'HUGGINGFACE_TOKEN',
      'OPENAI_API_KEY',
      'GROQ_API_KEY',
      'GOOGLE_GEMINI_API_KEY',
    ],
  },
  {
    label: 'Web Scraping',
    keys: [
      'FIRECRAWL_API_KEY',
    ],
  },
  {
    label: 'Social Platforms',
    keys: [
      'TWITTER_API_KEY',
      'TWITTER_API_SECRET',
      'TWITTER_BEARER_TOKEN',
      'META_APP_ID',
      'META_APP_SECRET',
      'LINKEDIN_CLIENT_ID',
      'LINKEDIN_CLIENT_SECRET',
      'TIKTOK_CLIENT_KEY',
      'TIKTOK_CLIENT_SECRET',
      'YOUTUBE_CLIENT_ID',
      'YOUTUBE_CLIENT_SECRET',
    ],
  },
  {
    label: 'Auth & Payments',
    keys: [
      'JWT_SECRET',
      'STRIPE_SECRET_KEY',
    ],
  },
  {
    label: 'Email & Storage',
    keys: ['RESEND_API_KEY', 'ENCRYPTION_KEY'],
  },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [systemKeys, setSystemKeys] = useState<Record<string, string>>({});
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [isSaving, setIsSaving] = useState<Record<string, boolean>>({});
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const token = getStoredToken();
      const authHeaders: Record<string, string> = {};
      if (token) authHeaders.Authorization = `Bearer ${token}`;
      const [healthRes, keysRes] = await Promise.all([
        fetch('/api/v1/admin/health', { headers: authHeaders }),
        fetch('/api/v1/admin/system-keys', { headers: authHeaders }),
      ]);
      if (healthRes.ok) setHealth(await healthRes.json());
      if (keysRes.ok) {
        const data: SystemKeys = await keysRes.json();
        setSystemKeys(data.keys);
      }
    } catch (err) {
      toast.error('Failed to load admin data');
    } finally {
      setIsLoading(false);
    }
  };

  const saveKey = async (keyName: string) => {
    const value = editValues[keyName];
    if (!value?.trim()) { toast.error('Key value cannot be empty'); return; }
    setIsSaving(prev => ({ ...prev, [keyName]: true }));
    try {
      const token = getStoredToken();
      const res = await fetch('/api/v1/admin/system-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ key_name: keyName, key_value: value.trim() }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
      toast.success(`${keyName} saved (runtime). Update .env to persist.`);
      setEditValues(prev => ({ ...prev, [keyName]: '' }));
      await loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to save key');
    } finally {
      setIsSaving(prev => ({ ...prev, [keyName]: false }));
    }
  };

  const toggleFlag = async (flag: string, value: boolean) => {
    try {
      const token = getStoredToken();
      const body: Record<string, unknown> = { [flag]: value };
      const res = await fetch('/api/v1/admin/feature-flags', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Failed to update flag');
      toast.success(`${flag} ${value ? 'enabled' : 'disabled'}`);
      await loadData();
    } catch {
      toast.error('Failed to update feature flag');
    }
  };

  const triggerGeneration = async () => {
    setIsGenerating(true);
    try {
      const token = getStoredToken();
      const res = await fetch('/api/v1/admin/trigger-generation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ window: 'manual' }),
      });
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      toast.success(`Generation triggered! Task ID: ${data.task_id}`);
    } catch {
      toast.error('Failed to trigger generation');
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  const flags = health?.feature_flags;

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-violet-600" />
            Admin Panel
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            System configuration — AmarktAI Marketing
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData}>
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Stats */}
      {health && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Users', value: health.stats.total_users, icon: Users, color: 'text-blue-500' },
            { label: 'Web Apps', value: health.stats.total_webapps, icon: Settings2, color: 'text-green-500' },
            { label: 'Content Items', value: health.stats.total_content, icon: FileText, color: 'text-purple-500' },
            { label: 'Posted', value: health.stats.posted_content, icon: BarChart3, color: 'text-orange-500' },
          ].map(stat => (
            <Card key={stat.label}>
              <CardContent className="p-4 flex items-center gap-3">
                <stat.icon className={`w-8 h-8 ${stat.color}`} />
                <div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-xs text-gray-500">{stat.label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Manual Trigger */}
      <Card className="border-violet-200 bg-violet-50">
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <p className="font-semibold text-violet-900">Manual Content Generation</p>
            <p className="text-sm text-violet-700">
              Trigger a content generation run for all users right now.
            </p>
          </div>
          <Button
            onClick={triggerGeneration}
            disabled={isGenerating}
            className="bg-violet-600 hover:bg-violet-700"
          >
            {isGenerating ? (
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            Run Now
          </Button>
        </CardContent>
      </Card>

      {/* Feature Flags */}
      {flags && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              Feature Flags
            </CardTitle>
            <CardDescription>
              Toggle platform features. Changes apply immediately (runtime only — update .env to persist).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { key: 'enable_auto_post', label: 'Auto-Post', desc: 'Automatically post approved content without human review' },
              { key: 'enable_auto_reply', label: 'Auto-Reply', desc: 'Automatically reply to comments and mentions' },
              { key: 'enable_ab_testing', label: 'A/B Testing', desc: 'Enable content variant A/B testing' },
              { key: 'enable_viral_prediction', label: 'Viral Prediction', desc: 'Show viral score predictions on content' },
              { key: 'enable_cost_tracking', label: 'Cost Tracking', desc: 'Track AI generation costs per user' },
            ].map(({ key, label, desc }) => (
              <div key={key} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="font-medium text-sm">{label}</p>
                  <p className="text-xs text-gray-500">{desc}</p>
                </div>
                <Switch
                  checked={!!flags[key as keyof typeof flags]}
                  onCheckedChange={(v) => toggleFlag(key, v)}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* API Keys */}
      {KEY_GROUPS.map(group => (
        <Card key={group.label}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="w-5 h-5 text-gray-500" />
              {group.label} API Keys
            </CardTitle>
            <CardDescription>
              Set system-level fallback keys. User keys in Integrations take priority.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {group.keys.map(keyName => {
              const currentMasked = systemKeys[keyName];
              const isSet = !!currentMasked;
              return (
                <div key={keyName} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Label className="text-xs font-mono font-semibold">{keyName}</Label>
                    {isSet ? (
                      <Badge variant="outline" className="text-green-600 border-green-300 text-xs">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> configured
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-gray-400 border-gray-200 text-xs">
                        <XCircle className="w-3 h-3 mr-1" /> not set
                      </Badge>
                    )}
                    {isSet && (
                      <span className="text-xs text-gray-400 font-mono">{currentMasked}</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Input
                        type={showValues[keyName] ? 'text' : 'password'}
                        placeholder={`Enter new ${keyName}…`}
                        value={editValues[keyName] || ''}
                        onChange={e =>
                          setEditValues(prev => ({ ...prev, [keyName]: e.target.value }))
                        }
                        className="text-xs font-mono pr-10"
                      />
                      <button
                        type="button"
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        onClick={() =>
                          setShowValues(prev => ({ ...prev, [keyName]: !prev[keyName] }))
                        }
                      >
                        {showValues[keyName] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <Button
                      size="sm"
                      disabled={!editValues[keyName] || isSaving[keyName]}
                      onClick={() => saveKey(keyName)}
                    >
                      {isSaving[keyName] ? <RefreshCw className="w-3 h-3 animate-spin" /> : 'Save'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}

      {/* Warning banner */}
      <Card className="border-amber-200 bg-amber-50">
        <CardContent className="p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
          <div className="text-sm text-amber-800">
            <p className="font-semibold mb-1">Runtime changes are not persisted</p>
            <p>
              Keys and flags set here apply to the running process only. To make them
              permanent, add them to <code className="bg-amber-100 px-1 rounded">backend/.env</code>{' '}
              and restart the server.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
