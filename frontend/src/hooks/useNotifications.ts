import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';

export interface Notification {
  id: number;
  type: string;
  severity: string;
  title: string;
  body: string;
  ticker?: string;
  sector?: string;
  read: boolean;
  createdAt: string;
  webhookSent: boolean;
  emailSent: boolean;
}

export interface NotificationConfig {
  id: number;
  webhookUrl?: string;
  email?: string;
  enabledTypes: string[];
  minSeverity: string;
}

// Normalize API response to camelCase
function normalizeNotification(notif: any): Notification {
  return {
    id: notif.id,
    type: notif.type,
    severity: notif.severity,
    title: notif.title,
    body: notif.body,
    ticker: notif.ticker,
    sector: notif.sector,
    read: notif.read,
    createdAt: notif.created_at || notif.createdAt,
    webhookSent: notif.webhook_sent || notif.webhookSent || false,
    emailSent: notif.email_sent || notif.emailSent || false,
  };
}

function normalizeConfig(config: any): NotificationConfig {
  return {
    id: config.id,
    webhookUrl: config.webhook_url || config.webhookUrl,
    email: config.email,
    enabledTypes: config.enabled_types || config.enabledTypes || [],
    minSeverity: config.min_severity || config.minSeverity,
  };
}

export function useNotifications(limit: number = 50, unreadOnly: boolean = false) {
  return useQuery({
    queryKey: ['notifications', limit, unreadOnly],
    queryFn: async () => {
      const { data } = await api.get('/notifications', {
        params: { limit, unread_only: unreadOnly },
      });
      return (Array.isArray(data) ? data : []).map(normalizeNotification);
    },
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
}

export function useNotificationCount() {
  return useQuery({
    queryKey: ['notification-count'],
    queryFn: async () => {
      const { data } = await api.get('/notifications/count');
      return data.unread;
    },
    staleTime: 15 * 1000, // 15 seconds
    refetchInterval: 15 * 1000, // Refetch every 15 seconds
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: number) => {
      const { data } = await api.post(`/notifications/read/${notificationId}`);
      return normalizeNotification(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notification-count'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/notifications/read-all');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notification-count'] });
    },
  });
}

export function useNotificationConfig() {
  return useQuery({
    queryKey: ['notification-config'],
    queryFn: async () => {
      const { data } = await api.get('/notifications/config');
      return normalizeConfig(data);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useUpdateNotificationConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config: Partial<NotificationConfig>) => {
      const payload = {
        webhook_url: config.webhookUrl,
        email: config.email,
        enabled_types: config.enabledTypes,
        min_severity: config.minSeverity,
      };
      const { data } = await api.put('/notifications/config', payload);
      return normalizeConfig(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-config'] });
    },
  });
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: async (webhookUrl: string) => {
      const { data } = await api.post('/notifications/test-webhook', {
        webhook_url: webhookUrl,
      });
      return data;
    },
  });
}
