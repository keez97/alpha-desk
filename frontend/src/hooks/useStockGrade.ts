import { useMutation } from '@tanstack/react-query';
import { gradeStock } from '../lib/api';

export function useStockGrade() {
  return useMutation({
    mutationFn: (ticker: string) => gradeStock(ticker),
  });
}
