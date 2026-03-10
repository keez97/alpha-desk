import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';

export interface RotationAlert {
  id?: number;
  ticker: string;
  sector: string;
  alertType: 'quadrant_change' | 'momentum_reversal' | 'breakout' | 'breakdown';
  fromQuadrant?: string | null;
  toQuadrant?: string | null;
  rsRatio: number;
  rsMomentum: number;
  description: string;
  severity: 'info' | 'warning' | 'critical';
  createdAt: string;
  acknowledged: boolean;
}

interface RotationAlertsResponse {
  alerts: RotationAlert[];
  benchmark: string;
  weeks: number;
  timestamp: string;
}

interface AlertHistoryResponse {
  alerts: RotationAlert[];
  total: number;
  timestamp: string;
}

interface AlertsScanResponse {
  alerts_generated: number;
  alerts_persisted: number;
  alerts: RotationAlert[];
}

// Normalize API response to camelCase
function normalizeAlert(alert: any): RotationAlert {
  return {
    id: alert.id,
    ticker: alert.ticker,
    sector: alert.sector,
    alertType: alert.alert_type || alert.alertType,
    fromQuadrant: alert.from_quadrant || alert.fromQuadrant,
    toQuadrant: alert.to_quadrant || alert.toQuadrant,
    rsRatio: alert.rs_ratio || alert.rsRatio,
    rsMomentum: alert.rs_momentum || alert.rsMomentum,
    description: alert.description,
    severity: alert.severity,
    createdAt: alert.created_at || alert.createdAt,
    acknowledged: alert.acknowledged || false,
  };
}

export function useRotationAlerts(benchmark: string = 'SPY', weeks: number = 10) {
  return useQuery({
    queryKey: ['rotation-alerts', benchmark, weeks],
    queryFn: async () => {
      const { data } = await api.get('/rotation-alerts', {
        params: { benchmark, weeks },
      });
      return {
        ...data,
        alerts: (data.alerts || []).map(normalizeAlert),
      } as RotationAlertsResponse;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
  });
}

export function useAlertHistory(limit: number = 100, severity?: string) {
  return useQuery({
    queryKey: ['rotation-alerts-history', limit, severity],
    queryFn: async () => {
      const { data } = await api.get('/rotation-alerts/history', {
        params: { limit, ...(severity && { severity }) },
      });
      return {
        ...data,
        alerts: (data.alerts || []).map(normalizeAlert),
      } as AlertHistoryResponse;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useScanForAlerts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params?: { benchmark?: string; weeks?: number }) => {
      const { data } = await api.post('/rotation-alerts/scan', null, {
        params: params || {},
      });
      return {
        ...data,
        alerts: (data.alerts || []).map(normalizeAlert),
      } as AlertsScanResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rotation-alerts'] });
      queryClient.invalidateQueries({ queryKey: ['rotation-alerts-history'] });
    },
  });
}

// Helper hook to count alerts by severity
export function useAlertSummary(alerts: RotationAlert[] | undefined) {
  return {
    total: alerts?.length ?? 0,
    critical: alerts?.filter(a => a.severity === 'critical').length ?? 0,
    warning: alerts?.filter(a => a.severity === 'warning').length ?? 0,
    info: alerts?.filter(a => a.severity === 'info').length ?? 0,
    highestSeverity: alerts && alerts.length > 0
      ? (alerts.some(a => a.severity === 'critical')
          ? 'critical'
          : alerts.some(a => a.severity === 'warning')
          ? 'warning'
          : 'info')
      : 'none',
  };
}
