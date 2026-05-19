import { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  Camera,
  Cloud,
  Instagram,
  Linkedin,
  Loader2,
  MessageCircle,
  Music,
  Pin,
  Send,
  Twitter,
  Youtube,
  Facebook,
  AtSign,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getStoredToken } from '@/lib/auth';

interface PlatformStatus {
  ui_status: string;
  can_post_now: boolean;
  missing: string[];
  posting_supported?: boolean;
}

interface ReadinessResponse {
  social_platforms?: Record<string, PlatformStatus>;
  oauth: Record<string, string>;
}

interface IntegrationStatus {
  platform: string;
  is_connected: boolean;
  platform_username: string | null;
}

const platforms = [
  { id: 'youtube', name: 'YouTube', icon: Youtube },
  { id: 'tiktok', name: 'TikTok', icon: Music },
  { id: 'instagram', name: 'Instagram', icon: Instagram },
  { id: 'facebook', name: 'Facebook', icon: Facebook },
  { id: 'twitter', name: 'X / Twitter', icon: Twitter },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin },
  { id: 'pinterest', name: 'Pinterest', icon: Pin },
  { id: 'reddit', name: 'Reddit', icon: MessageCircle },
  { id: 'bluesky', name: 'Bluesky', icon: Cloud },
  { id: 'threads', name: 'Threads', icon: AtSign },
  { id: 'telegram', name: 'Telegram', icon: Send },
  { id: 'snapchat', name: 'Snapchat', icon: Camera },
] as const;

export default function PlatformsPage() {
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const token = getStoredToken();
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const [readinessRes, integrationsRes] = await Promise.all([
          fetch('/api/v1/settings/readiness', { headers }),
          fetch('/api/v1/integrations/platforms', { headers }),
        ]);
        if (readinessRes.ok) setReadiness(await readinessRes.json() as ReadinessResponse);
        if (integrationsRes.ok) setIntegrations(await integrationsRes.json() as IntegrationStatus[]);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Platform posting status</h2>
        <p className="text-gray-500">
          This page is read-only. Manage real OAuth connections from Integrations.
        </p>
      </div>

      <Card className="border-amber-200 bg-amber-50/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            Unsupported manual connection flow removed
          </CardTitle>
          <CardDescription>
            Platforms only become postable after a valid OAuth connection, token, scopes, and platform target are present.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/dashboard/integrations">
              Open Integrations
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {platforms.map((platform) => {
          const Icon = platform.icon;
          const posting = readiness?.social_platforms?.[platform.id];
          const integration = integrations.find((item) => item.platform === platform.id);
          const oauthConfigured = readiness?.oauth?.[platform.id] === 'configured';

          return (
            <Card key={platform.id}>
              <CardContent className="space-y-3 p-5">
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
                  <Badge variant={posting?.can_post_now ? 'default' : 'outline'}>
                    {posting?.ui_status || 'Needs connection'}
                  </Badge>
                </div>

                <div className="space-y-1 text-sm text-gray-600">
                  <p>OAuth credentials: {oauthConfigured ? 'configured' : 'not_configured'}</p>
                  <p>User connection: {integration?.is_connected ? 'connected' : 'not connected'}</p>
                  {posting?.missing?.length ? (
                    <p>Blocked by: {posting.missing.join(', ')}</p>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
