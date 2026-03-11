import { useQuery } from '@tanstack/react-query';
import {
  fetchScenarioRisk,
  type HistoricalAnalog,
  type Scenario,
  type ScenarioRiskData,
} from '../lib/api';

export type { HistoricalAnalog, Scenario, ScenarioRiskData };

export function useScenarioRisk() {
  return useQuery({
    queryKey: ['scenarioRisk'],
    queryFn: fetchScenarioRisk,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}
