import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchReportList, fetchReport, deleteReport, generateWeeklyReportSSE } from '../lib/api';
import type { Report } from '../lib/api';
import { useState, useCallback } from 'react';

export function useReportList() {
  return useQuery({
    queryKey: ['reports'],
    queryFn: fetchReportList,
    staleTime: 5 * 60 * 1000,
  });
}

export function useReport(id: string | null) {
  return useQuery({
    queryKey: ['report', id],
    queryFn: () => fetchReport(id!),
    enabled: !!id,
  });
}

export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteReport,
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: ['report', id] });
      queryClient.setQueryData(['reports'], (old: unknown[] | undefined) => {
        return old ? old.filter((r: any) => r.id !== id) : [];
      });
    },
  });
}

interface SSESection {
  title: string;
  content: string;
}

export function useGenerateWeeklyReport() {
  const [sections, setSections] = useState<SSESection[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const generate = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    setSections([]);

    try {
      const eventSourceUrl = generateWeeklyReportSSE();
      const eventSource = new EventSource(eventSourceUrl);

      eventSource.addEventListener('section', (event) => {
        try {
          const section = JSON.parse(event.data) as SSESection;
          setSections((prev) => [...prev, section]);
        } catch (err) {
          console.error('Failed to parse section:', err);
        }
      });

      eventSource.addEventListener('complete', (event) => {
        try {
          const report = JSON.parse(event.data) as Report;
          queryClient.setQueryData(['reports'], (old: unknown[] | undefined) => {
            return old ? [report, ...old] : [report];
          });
          eventSource.close();
          setIsGenerating(false);
        } catch (err) {
          console.error('Failed to parse complete event:', err);
          eventSource.close();
          setIsGenerating(false);
        }
      });

      eventSource.addEventListener('error', () => {
        setError('Failed to generate report');
        eventSource.close();
        setIsGenerating(false);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsGenerating(false);
    }
  }, [queryClient]);

  return {
    generate,
    sections,
    isGenerating,
    error,
  };
}
