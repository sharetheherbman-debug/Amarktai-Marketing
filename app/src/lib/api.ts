/**
 * AmarktAI Marketing – Real API client
 *
 * All calls go to the backend via /api/v1 (proxied through Nginx or Vite's
 * dev-server proxy).  No mock data is used here; the pricingPlans and
 * platformInfo static config remain in mockData.ts as they are UI-only.
 */

import type {
  WebApp,
  MediaAsset,
  PlatformConnection,
  Content,
  AnalyticsSummary,
  PlatformStats,
  DailyStat,
  Platform,
  Lead,
  LeadStats,
} from '@/types';
import { getStoredToken } from '@/lib/auth';

// ─── Base helpers ────────────────────────────────────────────────────────────

const BASE = '/api/v1';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeaders, ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Convert snake_case backend object to camelCase frontend type. */
function toCamel(obj: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [
      k.replace(/_([a-z])/g, (_, c) => c.toUpperCase()),
      v,
    ])
  );
}

function mapWebApp(raw: Record<string, unknown>): WebApp {
  const c = toCamel(raw);
  return {
    id: c.id as string,
    userId: c.userId as string,
    name: c.name as string,
    url: c.url as string,
    description: c.description as string,
    category: c.category as string,
    targetAudience: c.targetAudience as string,
    keyFeatures: (c.keyFeatures as string[]) ?? [],
    logo: c.logo as string | undefined,
    isActive: c.isActive as boolean,
    brandVoice: (c.brandVoice as string) ?? undefined,
    marketLocation: (c.marketLocation as string) ?? undefined,
    contentGoals: (c.contentGoals as string) ?? undefined,
    scraperSourceUrls: (c.scraperSourceUrls as string[]) ?? undefined,
    scrapedData: (c.scrapedData as Record<string, unknown>) ?? null,
    mediaAssets: (c.mediaAssets as MediaAsset[]) ?? [],
    createdAt: c.createdAt as string,
    updatedAt: (c.updatedAt as string) ?? c.createdAt as string,
  };
}

function mapPlatform(raw: Record<string, unknown>): PlatformConnection {
  const c = toCamel(raw);
  return {
    id: c.id as string,
    userId: c.userId as string,
    platform: c.platform as Platform,
    accountName: c.accountName as string,
    accountId: c.accountId as string,
    isActive: c.isActive as boolean,
    connectedAt: c.connectedAt as string,
    expiresAt: c.expiresAt as string | undefined,
  };
}

function mapContent(raw: Record<string, unknown>): Content {
  const c = toCamel(raw);
  // Build performance object from flat columns
  const performance =
    c.views != null
      ? {
          views: (c.views as number) ?? 0,
          likes: (c.likes as number) ?? 0,
          comments: (c.comments as number) ?? 0,
          shares: (c.shares as number) ?? 0,
          clicks: (c.clicks as number) ?? 0,
          ctr: (c.ctr as number) ?? 0,
        }
      : undefined;

  return {
    id: c.id as string,
    userId: c.userId as string,
    webappId: c.webappId as string,
    platform: c.platform as Platform,
    type: c.type as Content['type'],
    status: c.status as Content['status'],
    title: c.title as string,
    caption: c.caption as string,
    hashtags: (c.hashtags as string[]) ?? [],
    mediaUrls: (c.mediaUrls as string[]) ?? [],
    scheduledFor: c.scheduledFor as string | undefined,
    postedAt: c.postedAt as string | undefined,
    performance,
    generationMetadata: (c.generationMetadata as Record<string, unknown>) ?? undefined,
    createdAt: c.createdAt as string,
    updatedAt: (c.updatedAt as string) ?? c.createdAt as string,
  };
}

// ─── Web Apps ────────────────────────────────────────────────────────────────

export const webAppApi = {
  getAll: async (): Promise<WebApp[]> => {
    const data = await apiFetch<Record<string, unknown>[]>('/webapps/');
    return data.map(mapWebApp);
  },

  getById: async (id: string): Promise<WebApp | null> => {
    try {
      const data = await apiFetch<Record<string, unknown>>(`/webapps/${id}`);
      return mapWebApp(data);
    } catch {
      return null;
    }
  },

  update: async (id: string, payload: Partial<WebApp>): Promise<WebApp> => {
    const body: Record<string, unknown> = {};
    if (payload.name !== undefined) body.name = payload.name;
    if (payload.url !== undefined) body.url = payload.url;
    if (payload.description !== undefined) body.description = payload.description;
    if (payload.category !== undefined) body.category = payload.category;
    if (payload.targetAudience !== undefined) body.target_audience = payload.targetAudience;
    if (payload.keyFeatures !== undefined) body.key_features = payload.keyFeatures;
    if (payload.logo !== undefined) body.logo = payload.logo;
    if (payload.isActive !== undefined) body.is_active = payload.isActive;
    if (payload.brandVoice !== undefined) body.brand_voice = payload.brandVoice;
    if (payload.marketLocation !== undefined) body.market_location = payload.marketLocation;
    if (payload.contentGoals !== undefined) body.content_goals = payload.contentGoals;
    if (payload.scraperSourceUrls !== undefined) body.scraper_source_urls = payload.scraperSourceUrls;
    const data = await apiFetch<Record<string, unknown>>(`/webapps/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
    return mapWebApp(data);
  },

  delete: async (id: string): Promise<void> => {
    await apiFetch<void>(`/webapps/${id}`, { method: 'DELETE' });
  },

  create: async (
    payload: Omit<WebApp, 'id' | 'userId' | 'createdAt' | 'updatedAt'>
  ): Promise<WebApp> => {
    const body = {
      name: payload.name,
      url: payload.url,
      description: payload.description,
      category: payload.category,
      target_audience: payload.targetAudience,
      key_features: payload.keyFeatures,
      logo: payload.logo,
      is_active: payload.isActive,
      brand_voice: payload.brandVoice ?? null,
      market_location: payload.marketLocation ?? null,
      content_goals: payload.contentGoals ?? null,
      scraper_source_urls: payload.scraperSourceUrls ?? null,
    };
    const data = await apiFetch<Record<string, unknown>>('/webapps/', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return mapWebApp(data);
  },

  uploadMedia: async (webAppId: string, file: File): Promise<MediaAsset> => {
    const token = getStoredToken();
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`/api/v1/webapps/${webAppId}/media`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error((err as { detail?: string }).detail || 'Upload failed');
    }
    const json = await res.json() as { asset: Record<string, unknown> };
    const a = toCamel(json.asset);
    return {
      id: a.id as string,
      name: a.name as string,
      url: a.url as string,
      type: a.type as string,
      size: a.size as number,
      uploadedAt: a.uploadedAt as string,
    };
  },

  deleteMedia: async (webAppId: string, assetId: string): Promise<void> => {
    await apiFetch<void>(`/webapps/${webAppId}/media/${assetId}`, { method: 'DELETE' });
  },
};

// ─── Platform Connections ────────────────────────────────────────────────────

export const platformApi = {
  getAll: async (): Promise<PlatformConnection[]> => {
    const data = await apiFetch<Record<string, unknown>[]>('/platforms/');
    return data.map(mapPlatform);
  },

  getByPlatform: async (platform: Platform): Promise<PlatformConnection | null> => {
    try {
      const data = await apiFetch<Record<string, unknown>>(`/platforms/${platform}`);
      return mapPlatform(data);
    } catch {
      return null;
    }
  },

  connect: async (platform: Platform, accountName: string, accountId?: string): Promise<PlatformConnection> => {
    let url = `/platforms/${platform}/connect?account_name=${encodeURIComponent(accountName)}`;
    if (accountId) url += `&account_id=${encodeURIComponent(accountId)}`;
    const data = await apiFetch<Record<string, unknown>>(url, { method: 'POST' });
    return mapPlatform(data);
  },

  disconnect: async (platform: Platform): Promise<void> => {
    await apiFetch<void>(`/platforms/${platform}/disconnect`, { method: 'POST' });
  },
};

// ─── Content ─────────────────────────────────────────────────────────────────

export const contentApi = {
  getAll: async (status?: Content['status']): Promise<Content[]> => {
    const qs = status ? `?status=${status}` : '';
    const data = await apiFetch<Record<string, unknown>[]>(`/content/${qs}`);
    return data.map(mapContent);
  },

  getPending: async (): Promise<Content[]> => {
    const data = await apiFetch<Record<string, unknown>[]>('/content/pending');
    return data.map(mapContent);
  },

  getById: async (id: string): Promise<Content | null> => {
    try {
      const data = await apiFetch<Record<string, unknown>>(`/content/${id}`);
      return mapContent(data);
    } catch {
      return null;
    }
  },

  approve: async (id: string): Promise<Content> => {
    const data = await apiFetch<Record<string, unknown>>(`/content/${id}/approve`, {
      method: 'POST',
    });
    return mapContent(data);
  },

  reject: async (id: string): Promise<Content> => {
    const data = await apiFetch<Record<string, unknown>>(`/content/${id}/reject`, {
      method: 'POST',
    });
    return mapContent(data);
  },

  approveAll: async (ids: string[]): Promise<void> => {
    await apiFetch<void>('/content/approve-all', {
      method: 'POST',
      body: JSON.stringify(ids),
    });
  },

  updateCaption: async (id: string, caption: string): Promise<Content> => {
    const data = await apiFetch<Record<string, unknown>>(`/content/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ caption }),
    });
    return mapContent(data);
  },

  generate: async (webappId: string, platform: Platform): Promise<Content> => {
    const data = await apiFetch<Record<string, unknown>>(
      `/content/generate?webapp_id=${webappId}&platform=${platform}`,
      { method: 'POST' }
    );
    return mapContent(data);
  },
};

// ─── Analytics ───────────────────────────────────────────────────────────────

function mapAnalyticsSummary(raw: Record<string, unknown>): AnalyticsSummary {
  const rawPlatforms = (raw.platform_breakdown as Record<string, Record<string, unknown>>) ?? {};
  const platformBreakdown: Record<string, PlatformStats> = {};
  for (const [platform, stats] of Object.entries(rawPlatforms)) {
    platformBreakdown[platform] = {
      posts: (stats.posts as number) ?? 0,
      views: (stats.views as number) ?? 0,
      engagement: (stats.engagement as number) ?? 0,
      ctr: (stats.ctr as number) ?? 0,
    };
  }
  const dailyStats: DailyStat[] = ((raw.daily_stats as Record<string, unknown>[]) ?? []).map((d) => ({
    date: d.date as string,
    posts: (d.posts as number) ?? 0,
    views: (d.views as number) ?? 0,
    engagement: (d.engagement as number) ?? 0,
  }));
  return {
    totalPosts: (raw.total_posts as number) ?? 0,
    totalViews: (raw.total_views as number) ?? 0,
    totalEngagement: (raw.total_engagement as number) ?? 0,
    avgCtr: (raw.avg_ctr as number) ?? 0,
    platformBreakdown: platformBreakdown as Record<Platform, PlatformStats>,
    dailyStats,
    learningActive: (raw.learning_active as boolean) ?? false,
    metricsRecords: (raw.metrics_records as number) ?? 0,
  };
}

export const analyticsApi = {
  getSummary: async (): Promise<AnalyticsSummary> => {
    const raw = await apiFetch<Record<string, unknown>>('/analytics/summary');
    return mapAnalyticsSummary(raw);
  },

  getPlatformStats: async (
    platform: Platform
  ): Promise<AnalyticsSummary['platformBreakdown'][Platform]> => {
    return apiFetch(`/analytics/platform/${platform}`);
  },

  upsertManualMetrics: async (payload: {
    content_id?: string;
    platform: string;
    metric_date?: string;
    impressions: number;
    reach: number;
    clicks: number;
    likes: number;
    comments: number;
    shares: number;
    saves: number;
    conversions: number;
  }) => {
    return apiFetch('/analytics/manual-metrics', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  importMetricsCsv: async (file: File): Promise<{ ok: boolean; imported: number; learning_active: boolean }> => {
    const token = getStoredToken();
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE}/analytics/import-csv`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => res.statusText);
      throw new Error(`API ${res.status}: ${detail}`);
    }
    return res.json();
  },

  getLearningStatus: async (): Promise<{ learning_active: boolean; metrics_records: number; message: string }> => {
    return apiFetch('/analytics/learning-status');
  },

};

// ─── Leads ───────────────────────────────────────────────────────────────────

function mapLead(raw: Record<string, unknown>): Lead {
  const c = toCamel(raw);
  return {
    id: c.id as string,
    name: c.name as string | undefined,
    email: c.email as string,
    phone: c.phone as string | undefined,
    company: c.company as string | undefined,
    sourcePlatform: c.sourcePlatform as Platform | undefined,
    utmSource: c.utmSource as string | undefined,
    utmMedium: c.utmMedium as string | undefined,
    utmCampaign: c.utmCampaign as string | undefined,
    qualifiers: c.qualifiers as Record<string, string> | undefined,
    leadScore: (c.leadScore as number) ?? 0,
    isQualified: (c.isQualified as boolean) ?? false,
    status: (c.status as Lead['status']) ?? 'new',
    notes: c.notes as string | undefined,
    createdAt: c.createdAt as string,
  };
}

export const leadsApi = {
  getAll: async (params?: { status?: string; platform?: string; isQualified?: boolean }): Promise<Lead[]> => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.platform) qs.set('platform', params.platform);
    if (params?.isQualified !== undefined) qs.set('is_qualified', String(params.isQualified));
    const query = qs.toString() ? `?${qs.toString()}` : '';
    const data = await apiFetch<Record<string, unknown>[]>(`/leads/${query}`);
    return data.map(mapLead);
  },

  getStats: async (): Promise<LeadStats> => {
    const data = await apiFetch<Record<string, unknown>>('/leads/stats');
    const c = toCamel(data);
    return {
      total: c.total as number,
      qualified: c.qualified as number,
      converted: c.converted as number,
      qualificationRate: c.qualificationRate as number,
      conversionRate: c.conversionRate as number,
      byPlatform: c.byPlatform as Record<string, number>,
    };
  },

  update: async (id: string, update: Partial<Lead>): Promise<Lead> => {
    const data = await apiFetch<Record<string, unknown>>(`/leads/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        status: update.status,
        notes: update.notes,
        is_qualified: update.isQualified,
        lead_score: update.leadScore,
      }),
    });
    return mapLead(data);
  },

  delete: async (id: string): Promise<void> => {
    await apiFetch<void>(`/leads/${id}`, { method: 'DELETE' });
  },

  generateUtmLink: async (params: {
    base_url: string;
    campaign: string;
    platform: string;
    content_id?: string;
  }): Promise<{ utm_url: string; params: Record<string, string> }> => {
    return apiFetch('/leads/utm/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  exportCsv: (): void => {
    window.location.href = `${BASE}/leads/export/csv`;
  },
};

// ─── Integrations (platform OAuth) ───────────────────────────────────────────

export const integrationsApi = {
  getApiKeys: async (): Promise<{ id: string; key_name: string; is_active: boolean; created_at: string }[]> => {
    return apiFetch('/integrations/api-keys');
  },

  saveApiKey: async (key_name: string, key_value: string): Promise<void> => {
    await apiFetch('/integrations/api-keys', {
      method: 'POST',
      body: JSON.stringify({ key_name, key_value }),
    });
  },

  deleteApiKey: async (id: string): Promise<void> => {
    await apiFetch(`/integrations/api-keys/${id}`, { method: 'DELETE' });
  },

  getPlatforms: async () => {
    return apiFetch<Record<string, unknown>[]>('/integrations/platforms');
  },

  getConnectUrl: async (platform: Platform): Promise<{ auth_url: string }> => {
    return apiFetch(`/integrations/platforms/${platform}/connect`);
  },

  disconnectPlatform: async (platform: Platform): Promise<void> => {
    await apiFetch(`/integrations/platforms/${platform}/disconnect`, { method: 'POST' });
  },

  updatePlatformSettings: async (
    platform: Platform,
    settings: { auto_post_enabled?: boolean; auto_reply_enabled?: boolean }
  ): Promise<void> => {
    await apiFetch(`/integrations/platforms/${platform}`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    });
  },
};

// ─── Blog Posts ────────────────────────────────────────────────────────────────

export interface BlogPost {
  id: string;
  webappId?: string;
  title: string;
  slug?: string;
  metaDescription?: string;
  sections: { heading: string; content: string }[];
  targetKeywords: string[];
  ctaText?: string;
  ctaUrl?: string;
  readingTimeMins?: string;
  customTopic?: string;
  status: string;
  isPublished: boolean;
  publishedUrl?: string;
  createdAt: string;
}

function mapBlogPost(raw: Record<string, unknown>): BlogPost {
  const c = toCamel(raw);
  return {
    id: c.id as string,
    webappId: c.webappId as string | undefined,
    title: c.title as string,
    slug: c.slug as string | undefined,
    metaDescription: c.metaDescription as string | undefined,
    sections: (c.sections as { heading: string; content: string }[]) ?? [],
    targetKeywords: (c.targetKeywords as string[]) ?? [],
    ctaText: c.ctaText as string | undefined,
    ctaUrl: c.ctaUrl as string | undefined,
    readingTimeMins: c.readingTimeMins as string | undefined,
    customTopic: c.customTopic as string | undefined,
    status: (c.status as string) ?? 'draft',
    isPublished: (c.isPublished as boolean) ?? false,
    publishedUrl: c.publishedUrl as string | undefined,
    createdAt: c.createdAt as string,
  };
}

export const blogApi = {
  generate: async (params: {
    webapp_id: string;
    custom_topic?: string;
    custom_keywords?: string[];
  }): Promise<BlogPost> => {
    const data = await apiFetch<Record<string, unknown>>('/blog/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    return mapBlogPost(data);
  },

  getAll: async (): Promise<BlogPost[]> => {
    const data = await apiFetch<Record<string, unknown>[]>('/blog/');
    return data.map(mapBlogPost);
  },

  getById: async (id: string): Promise<BlogPost | null> => {
    try {
      const data = await apiFetch<Record<string, unknown>>(`/blog/${id}`);
      return mapBlogPost(data);
    } catch {
      return null;
    }
  },

  update: async (id: string, update: Partial<BlogPost>): Promise<BlogPost> => {
    const data = await apiFetch<Record<string, unknown>>(`/blog/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        title: update.title,
        meta_description: update.metaDescription,
        status: update.status,
        is_published: update.isPublished,
        published_url: update.publishedUrl,
      }),
    });
    return mapBlogPost(data);
  },

  delete: async (id: string): Promise<void> => {
    await apiFetch<void>(`/blog/${id}`, { method: 'DELETE' });
  },

  remixToSocial: async (id: string): Promise<{ message: string; platforms: string[] }> => {
    return apiFetch(`/blog/${id}/remix-to-social`, { method: 'POST' });
  },
};

// ─── Content batch generate-all ───────────────────────────────────────────────

export const contentBatchApi = {
  generateAll: async (): Promise<{ message: string; count: number; platforms: string[] }> => {
    return apiFetch('/content/generate-all', { method: 'POST' });
  },
};

// ─── Groups / Communities API ─────────────────────────────────────────────────

export interface BusinessGroup {
  id: string;
  webappId: string;
  platform: 'facebook' | 'reddit' | 'telegram' | 'discord' | 'linkedin';
  groupId?: string;
  groupName: string;
  groupUrl?: string;
  description?: string;
  status: 'suggested' | 'joined' | 'active' | 'paused' | 'removed';
  memberCount: number;
  postsSent: number;
  totalViews: number;
  totalEngagements: number;
  totalLeads: number;
  avgInteractionRate: number;
  keywordsUsed?: string;
  complianceNote?: string;
  createdAt: string;
}

function mapGroup(d: Record<string, unknown>): BusinessGroup {
  return {
    id: d.id as string,
    webappId: d.webapp_id as string,
    platform: d.platform as BusinessGroup['platform'],
    groupId: d.group_id as string | undefined,
    groupName: d.group_name as string,
    groupUrl: d.group_url as string | undefined,
    description: d.description as string | undefined,
    status: d.status as BusinessGroup['status'],
    memberCount: (d.member_count as number) || 0,
    postsSent: (d.posts_sent as number) || 0,
    totalViews: (d.total_views as number) || 0,
    totalEngagements: (d.total_engagements as number) || 0,
    totalLeads: (d.total_leads as number) || 0,
    avgInteractionRate: (d.avg_interaction_rate as number) || 0,
    keywordsUsed: d.keywords_used as string | undefined,
    complianceNote: d.compliance_note as string | undefined,
    createdAt: d.created_at as string,
  };
}

export const groupsApi = {
  list: async (webappId?: string, platform?: string, status?: string): Promise<BusinessGroup[]> => {
    const params = new URLSearchParams();
    if (webappId) params.set('webapp_id', webappId);
    if (platform) params.set('platform', platform);
    if (status) params.set('status_filter', status);
    const qs = params.toString();
    const data = await apiFetch<Record<string, unknown>[]>(`/groups${qs ? '?' + qs : ''}`);
    return data.map(mapGroup);
  },

  search: async (webappId: string, platform: string): Promise<{ found: number; saved: number; keywords_used: string }> => {
    return apiFetch('/groups/search', {
      method: 'POST',
      body: JSON.stringify({ webapp_id: webappId, platform }),
    });
  },

  confirmJoin: async (groupId: string, platformGroupId: string): Promise<BusinessGroup> => {
    const data = await apiFetch<Record<string, unknown>>(`/groups/${groupId}/confirm-join`, {
      method: 'POST',
      body: JSON.stringify({ group_id: platformGroupId }),
    });
    return mapGroup(data);
  },

  updateStatus: async (groupId: string, newStatus: string): Promise<{ id: string; status: string }> => {
    return apiFetch(`/groups/${groupId}/status?new_status=${newStatus}`, { method: 'PATCH' });
  },

  post: async (groupId: string, text: string, link?: string): Promise<{ success: boolean; post_id: string; url: string }> => {
    return apiFetch(`/groups/${groupId}/post`, {
      method: 'POST',
      body: JSON.stringify({ text, link }),
    });
  },

  delete: async (groupId: string): Promise<void> => {
    await apiFetch<void>(`/groups/${groupId}`, { method: 'DELETE' });
  },

  stats: async (): Promise<{
    total: number; active: number; suggested: number; joined: number;
    total_posts_sent: number; total_leads: number; by_platform: Record<string, { count: number; active: number; posts: number }>;
  }> => {
    return apiFetch('/groups/stats/summary');
  },
};

// ─── WebApp Scraping ──────────────────────────────────────────────────────────

export interface ScrapedData {
  scrapedAt: string;
  title: string;
  metaDescription: string;
  headings: string[];
  paragraphs: string[];
  socialLinks: string[];
  fullText: string;
  error: string | null;
  status: 'ok' | 'error';
}

export const scrapeApi = {
  scrapeWebapp: async (webappId: string): Promise<{ message: string; scraped_data: ScrapedData }> => {
    const raw = await apiFetch<{ message: string; scraped_data: Record<string, unknown> }>(
      `/webapps/${webappId}/scrape`,
      { method: 'POST' }
    );
    const d = raw.scraped_data;
    return {
      message: raw.message,
      scraped_data: {
        scrapedAt: d.scraped_at as string,
        title: d.title as string,
        metaDescription: d.meta_description as string,
        headings: (d.headings as string[]) ?? [],
        paragraphs: (d.paragraphs as string[]) ?? [],
        socialLinks: (d.social_links as string[]) ?? [],
        fullText: d.full_text as string,
        error: d.error as string | null,
        status: d.status as 'ok' | 'error',
      },
    };
  },
};

// ─── Platform Audit ───────────────────────────────────────────────────────────

export interface PlatformAudit {
  platform: string;
  accountName: string;
  accountId: string;
  connectedAt: string | null;
  accountAgeDays: number;
  accountType: 'new' | 'established';
  accountTypeLabel: string;
  algorithmInsights: {
    best_post_times: string[];
    content_priority: string[];
    algorithm_tips: string[];
    engagement_benchmarks: { good_rate: number; great_rate: number; unit: string };
    paid_ad_tips: string[];
  };
  recommendations: string[];
  canCreateBusinessPages: boolean;
  businessPageInfo: {
    max_pages_per_account: number;
    can_create: boolean;
    setup_steps: string[];
  } | null;
  autoPostEnabled: boolean;
  autoReplyEnabled: boolean;
  monthlyAdBudget: number;
}

export const platformAuditApi = {
  audit: async (platform: string): Promise<PlatformAudit> => {
    const raw = await apiFetch<Record<string, unknown>>(`/platforms/${platform}/audit`);
    return {
      platform: raw.platform as string,
      accountName: raw.account_name as string,
      accountId: raw.account_id as string,
      connectedAt: raw.connected_at as string | null,
      accountAgeDays: raw.account_age_days as number,
      accountType: raw.account_type as 'new' | 'established',
      accountTypeLabel: raw.account_type_label as string,
      algorithmInsights: raw.algorithm_insights as PlatformAudit['algorithmInsights'],
      recommendations: (raw.recommendations as string[]) ?? [],
      canCreateBusinessPages: raw.can_create_business_pages as boolean,
      businessPageInfo: raw.business_page_info as PlatformAudit['businessPageInfo'],
      autoPostEnabled: raw.auto_post_enabled as boolean,
      autoReplyEnabled: raw.auto_reply_enabled as boolean,
      monthlyAdBudget: raw.monthly_ad_budget as number,
    };
  },

  createBusinessPage: async (
    platform: string,
    body: { page_name: string; category: string; description?: string; website_url?: string }
  ): Promise<{
    status: string;
    platform: string;
    page_name: string;
    page_id: string;
    message: string;
    setup_steps: string[];
    max_pages_per_account: number;
  }> => {
    return apiFetch(`/platforms/${platform}/create-business-page`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};

// ─── Dashboard Feature APIs ──────────────────────────────────────────────────

/** AI Insights Feed */
export const insightsApi = {
  getAll: async (): Promise<{
    id: string;
    type: string;
    title: string;
    description: string;
    action?: string;
    impact: string;
    timestamp: string;
    read: boolean;
  }[]> => {
    return apiFetch('/dashboard/insights');
  },
};

/** Smart Scheduler */
export const schedulerApi = {
  getHeatmap: async (platform = 'all'): Promise<{
    time_slots: { hour: number; score: number; audience_count: number; engagement: number }[];
    best_slots: { hour: number; score: number; audience_count: number; engagement: number }[];
    platform: string;
  }> => {
    return apiFetch(`/dashboard/scheduler/heatmap?platform=${platform}`);
  },

  getScheduledPosts: async (): Promise<{
    id: string;
    title: string;
    platform: string;
    scheduled_time: string | null;
    status: string;
    predicted_engagement: number;
    optimal_score: number;
  }[]> => {
    return apiFetch('/dashboard/scheduler/posts');
  },
};

/** Viral Prediction */
export const viralPredictApi = {
  predict: async (body: {
    caption: string;
    hashtags: string[];
    platform: string;
    media_urls?: string[];
  }): Promise<{
    score: {
      overall: number;
      hook_strength: number;
      emotional_impact: number;
      shareability: number;
      timing: number;
      uniqueness: number;
    };
    viral_probability: number;
    estimated_reach: number;
    time_to_viral: string;
    factors: { positive: string[]; negative: string[] };
    recommendations: string[];
  }> => {
    return apiFetch('/dashboard/viral-predict', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};

/** Performance Prediction */
export const performancePredictApi = {
  predict: async (body: {
    caption: string;
    hashtags: string[];
    platform: string;
    media_urls?: string[];
  }): Promise<{
    predicted_views: number;
    predicted_engagement: number;
    predicted_ctr: number;
    confidence_score: number;
    risk_level: string;
    improvement_suggestions: string[];
  }> => {
    return apiFetch('/dashboard/performance-predict', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};

/** Content Calendar */
export const calendarApi = {
  getEvents: async (month?: string): Promise<{
    id: string;
    date: string | null;
    platform: string;
    title: string;
    status: string;
    time: string;
  }[]> => {
    const qs = month ? `?month=${month}` : '';
    return apiFetch(`/dashboard/calendar${qs}`);
  },
};

/** A/B Testing (wires to existing /ab-testing endpoints) */
export const abTestingApi = {
  getTests: async (status?: string, platform?: string): Promise<Record<string, unknown>[]> => {
    const qs = new URLSearchParams();
    if (status) qs.set('status', status);
    if (platform) qs.set('platform', platform);
    const query = qs.toString() ? `?${qs.toString()}` : '';
    return apiFetch(`/ab-testing/tests${query}`);
  },

  getStats: async (): Promise<Record<string, unknown>> => {
    return apiFetch('/ab-testing/stats');
  },

  createTest: async (body: {
    content_id: string;
    test_name: string;
    platform: string;
    test_hypothesis?: string;
    variants: Record<string, unknown>[];
  }): Promise<Record<string, unknown>> => {
    return apiFetch('/ab-testing/tests', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  updateTest: async (testId: string, update: Record<string, unknown>): Promise<Record<string, unknown>> => {
    return apiFetch(`/ab-testing/tests/${testId}`, {
      method: 'PATCH',
      body: JSON.stringify(update),
    });
  },
};

/** Content Remix / Repurposer (wires to existing /remix endpoints) */
export const remixApi = {
  create: async (body: {
    source_type: string;
    source_url?: string;
    source_text?: string;
    target_platforms: string[];
    webapp_id?: string;
  }): Promise<{ id: string; status: string; message: string }> => {
    return apiFetch('/remix/', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  getAll: async (): Promise<Record<string, unknown>[]> => {
    return apiFetch('/remix/');
  },

  getById: async (id: string): Promise<Record<string, unknown>> => {
    return apiFetch(`/remix/${id}`);
  },

  delete: async (id: string): Promise<void> => {
    await apiFetch<void>(`/remix/${id}`, { method: 'DELETE' });
  },
};

/** Competitor Intelligence */
export const competitorApi = {
  getData: async (): Promise<{
    competitors: Record<string, unknown>[];
    has_data: boolean;
    message: string | null;
  }> => {
    return apiFetch('/dashboard/competitors');
  },

  getTrends: async (): Promise<Record<string, unknown>[]> => {
    return apiFetch('/dashboard/competitors/trends');
  },
};
