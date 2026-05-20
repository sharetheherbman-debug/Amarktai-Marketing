/**
 * useWebapp — manages the user's list of webapps and the currently active one.
 *
 * - Fetches GET /api/v1/webapps on mount.
 * - Persists the active webapp id in localStorage under 'amarktai_active_webapp'.
 * - Returns { webapps, activeWebapp, setActiveWebapp, loading, error, reload }.
 */

import { useCallback, useEffect, useState } from 'react';
import { webAppApi } from '@/lib/api';
import type { WebApp } from '@/types';

const STORAGE_KEY = 'amarktai_active_webapp';

export interface UseWebappReturn {
  webapps: WebApp[];
  activeWebapp: WebApp | null;
  activeWebappId: string | null;
  setActiveWebapp: (id: string) => void;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useWebapp(): UseWebappReturn {
  const [webapps, setWebapps] = useState<WebApp[]>([]);
  const [activeWebappId, setActiveWebappIdState] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY)
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const list = await webAppApi.getAll();
      setWebapps(list);

      // Auto-select: keep saved id if still valid, otherwise pick first
      const savedId = localStorage.getItem(STORAGE_KEY);
      const valid = list.find((w) => w.id === savedId);
      if (valid) {
        setActiveWebappIdState(valid.id);
      } else if (list.length > 0) {
        setActiveWebappIdState(list[0].id);
        localStorage.setItem(STORAGE_KEY, list[0].id);
      } else {
        setActiveWebappIdState(null);
      }
    } catch {
      setError('Failed to load businesses. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const handler = () => {
      void load();
    };
    window.addEventListener('amarktai:webapps-changed', handler);
    return () => window.removeEventListener('amarktai:webapps-changed', handler);
  }, [load]);

  const setActiveWebapp = useCallback((id: string) => {
    setActiveWebappIdState(id);
    localStorage.setItem(STORAGE_KEY, id);
  }, []);

  const activeWebapp = webapps.find((w) => w.id === activeWebappId) ?? webapps[0] ?? null;

  return {
    webapps,
    activeWebapp,
    activeWebappId: activeWebapp?.id ?? null,
    setActiveWebapp,
    loading,
    error,
    reload: load,
  };
}
