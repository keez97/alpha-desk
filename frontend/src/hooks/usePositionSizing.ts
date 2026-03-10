import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export interface FactorBreakdown {
  name: string;
  value: number;
  percentile: number;
  weight: number;
  contribution: number;
}

export interface PositionSizing {
  ticker: string;
  compositeScore: number;
  sizeCategory: string;
  sizePct: number;
  positionValue: number;
  kellyFraction: number;
  stopLoss: number;
  factorBreakdown: FactorBreakdown[];
  riskNotes: string[];
}

async function getPositionSizing(
  ticker: string,
  portfolioValue: number = 100000
): Promise<PositionSizing> {
  const { data } = await axios.get(`/api/position-sizing/${ticker}`, {
    params: { portfolio_value: portfolioValue },
  });
  return data;
}

export function usePositionSizing(
  ticker: string | null,
  portfolioValue: number = 100000
) {
  return useQuery({
    queryKey: ['position-sizing', ticker, portfolioValue],
    queryFn: () => getPositionSizing(ticker!, portfolioValue),
    enabled: !!ticker,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}
