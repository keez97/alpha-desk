/**
 * Prefetch all morning brief data in a SINGLE HTTP request.
 * Seeds the API response cache so individual panel hooks find pre-fetched data.
 */
import { useEffect, useRef, useState } from 'react';
import api, { seedApiCache } from '../lib/api';

export function usePrefetchMorningBrief() {
  const fetched = useRef(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (fetched.current) return;
    fetched.current = true;

    (async () => {
      try {
        const { data } = await api.get('/morning-brief/all');
        seedApiCache(data);
        setReady(true);
        console.log('[prefetch] Morning brief data loaded');
      } catch (e: any) {
        console.error('[prefetch] Failed:', e.message);
        setError(e);
        setReady(true); // let individual hooks try their own fetches
      }
    })();
  }, []);

  return { ready, error };
}
