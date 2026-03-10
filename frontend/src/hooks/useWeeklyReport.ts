import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchReportList, fetchReport, deleteReport } from '../lib/api';
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
      const response = await fetch('/api/weekly-report/generate', {
        method: 'POST',
        headers: { 'Accept': 'text/event-stream' },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              if (currentEvent === 'section') {
                setSections((prev) => [...prev, parsed as SSESection]);
              } else if (currentEvent === 'complete') {
                queryClient.invalidateQueries({ queryKey: ['reports'] });
                setIsGenerating(false);
                return;
              }
            } catch (e) {
              // Ignore malformed JSON
            }
            currentEvent = '';
          }
        }
      }

      setIsGenerating(false);
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
