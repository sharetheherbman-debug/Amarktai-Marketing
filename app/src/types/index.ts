// Types for AmarktAI Marketing Platform

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  plan: 'free' | 'pro' | 'business' | 'enterprise';
  createdAt: string;
}

export interface WebApp {
  id: string;
  userId: string;
  name: string;
  url: string;
  description: string;
  category: string;
  targetAudience: string;
  keyFeatures: string[];
  logo?: string;
  isActive: boolean;
  brandVoice?: string;
  marketLocation?: string;
  contentGoals?: string;
  scraperSourceUrls?: string[];
  scrapedData?: Record<string, unknown> | null;
  mediaAssets?: MediaAsset[];
  createdAt: string;
  updatedAt: string;
}

export interface MediaAsset {
  id: string;
  name: string;
  url: string;
  type: string;
  size: number;
  uploadedAt: string;
}

export type Platform =
  | 'youtube'
  | 'tiktok'
  | 'instagram'
  | 'facebook'
  | 'twitter'
  | 'linkedin'
  | 'pinterest'
  | 'reddit'
  | 'bluesky'
  | 'threads'
  | 'telegram'
  | 'snapchat';

export interface PlatformConnection {
  id: string;
  userId: string;
  platform: Platform;
  accountName: string;
  accountId: string;
  isActive: boolean;
  connectedAt: string;
  expiresAt?: string;
  monthlyAdBudget?: number;
  dailyAdBudget?: number;
  adBudgetCurrency?: string;
  adAccountId?: string;
  autoPostEnabled?: boolean;
  autoReplyEnabled?: boolean;
  postingSchedule?: Record<string, unknown>;
}

export type ContentStatus = 'pending' | 'approved' | 'rejected' | 'posted' | 'failed' | 'scheduled';
export type ContentType = 'video' | 'image' | 'carousel' | 'text';

export interface Content {
  id: string;
  userId: string;
  webappId: string;
  platform: Platform;
  type: ContentType;
  status: ContentStatus;
  title: string;
  caption: string;
  hashtags: string[];
  mediaUrls: string[];
  scheduledFor?: string;
  postedAt?: string;
  performance?: ContentPerformance;
  generationMetadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface ContentLibraryItem {
  id: string;
  userId: string;
  webappId: string;
  businessName: string;
  campaignId?: string;
  sourceRoute: string;
  sourceAction: string;
  generatedBy: string;
  platform: Platform;
  format: string;
  status: string;
  title: string;
  previewTitle?: string;
  previewSummary?: string;
  caption: string;
  body: string;
  hooks?: string[];
  hashtags: string[];
  cta?: string;
  imagePrompt?: string;
  videoScript?: string;
  shotList: string[];
  voiceoverScript?: string;
  avatarScript?: string;
  thumbnailPrompt?: string;
  carouselSlides: string[];
  platformFitScore?: number;
  complianceNotes: string[];
  providerAttempted?: string;
  providerActual?: string;
  modelActual?: string;
  providerSelected?: string;
  modelSelected?: string;
  fallbackChain?: string[];
  taskUsed?: string;
  capabilityUsed?: string;
  generationStatus: string;
  degraded: boolean;
  reason?: string;
  variationSeed?: string;
  uniquenessScore?: number;
  businessGroundingScore?: number;
  hashtagRelevanceScore?: number;
  creativeRelevanceScore?: number;
  warnings?: string[];
  rejectionReason?: string;
  assetGenerationStatus?: string;
  mediaJobIds: string[];
  mediaAssetIds: string[];
  mediaUrls: string[];
  sourceBusinessSnapshot?: Record<string, unknown>;
  parentContentId?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface ContentPerformance {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  clicks: number;
  ctr: number;
}

export interface AnalyticsSummary {
  totalPosts: number;
  totalViews: number;
  totalEngagement: number;
  avgCtr: number;
  platformBreakdown: Record<Platform, PlatformStats>;
  dailyStats: DailyStat[];
  learningActive?: boolean;
  metricsRecords?: number;
}

export interface PlatformStats {
  posts: number;
  views: number;
  engagement: number;
  ctr: number;
}

export interface DailyStat {
  date: string;
  posts: number;
  views: number;
  engagement: number;
}

export interface Lead {
  id: string;
  name?: string;
  email: string;
  phone?: string;
  company?: string;
  sourcePlatform?: Platform;
  utmSource?: string;
  utmMedium?: string;
  utmCampaign?: string;
  qualifiers?: Record<string, string>;
  leadScore: number;
  isQualified: boolean;
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
  notes?: string;
  createdAt: string;
}

export interface LeadStats {
  total: number;
  qualified: number;
  converted: number;
  qualificationRate: number;
  conversionRate: number;
  byPlatform: Record<string, number>;
}

export interface PricingPlan {
  id: string;
  name: string;
  price: number;
  description: string;
  features: string[];
  limits: {
    webapps: number;
    platforms: number;
    postsPerDay: number;
    imagesPerMonth: number;
    videosPerMonth: number;
  };
  highlighted?: boolean;
}

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
