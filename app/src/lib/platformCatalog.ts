import type { Platform } from '@/types';

export interface PlatformCatalogItem {
  id: Platform;
  label: string;
}

export const PLATFORM_CATALOG: PlatformCatalogItem[] = [
  { id: 'instagram', label: 'Instagram' },
  { id: 'facebook', label: 'Facebook' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'twitter', label: 'X / Twitter' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'reddit', label: 'Reddit' },
  { id: 'pinterest', label: 'Pinterest' },
  { id: 'threads', label: 'Threads' },
  { id: 'bluesky', label: 'Bluesky' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'snapchat', label: 'Snapchat' },
];
