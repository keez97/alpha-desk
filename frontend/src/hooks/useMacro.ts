import { useQuery } from '@tanstack/react-query';
import { fetchMacro } from '../lib/api';

export function useMacro() {
  return useQuery({
    queryKey: ['macro'],
    queryFn: fetchMacro,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000,
  });
}
