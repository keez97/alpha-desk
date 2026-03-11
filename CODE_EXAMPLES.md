# Correlation Heat Map Feature - Code Examples

This document provides code snippets from each implementation file to demonstrate key functionality.

## Backend Examples

### correlation_engine.py - Main Calculation

```python
def calculate_correlation_matrix(lookback_days: int = 90) -> Dict[str, Any]:
    """
    Calculate correlation matrix for sector ETFs.

    - Fetches price data from yfinance
    - Computes daily returns
    - Calculates Pearson correlation matrix
    - Identifies pairs trades and hedging opportunities
    """
    try:
        # Fetch price data for all sector ETFs
        price_data = {}
        valid_tickers = []

        for ticker in SECTOR_TICKERS:
            try:
                history = get_history(ticker, period="1y")
                if not history or len(history) < lookback_days:
                    logger.warning(f"Insufficient data for {ticker}")
                    continue

                # Extract close prices and reverse to oldest first
                prices = [h["close"] for h in history]
                prices.reverse()

                # Take only the lookback period
                prices = prices[-lookback_days:]

                if len(prices) >= lookback_days:
                    price_data[ticker] = prices
                    valid_tickers.append(ticker)
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {e}")
                continue

        # Create price dataframe
        df_prices = pd.DataFrame(price_data)

        # Calculate daily returns
        df_returns = df_prices.pct_change().dropna()

        # Calculate correlation matrix
        corr_matrix = df_returns.corr().values.tolist()

        # Find pairs trade opportunities
        pairs_trades = _identify_pairs_trades(valid_tickers, sectors, corr_matrix)

        # Find hedging opportunities
        hedging_pairs = _identify_hedging_pairs(valid_tickers, sectors, corr_matrix)

        return {
            "matrix": corr_matrix,
            "tickers": valid_tickers,
            "sectors": sectors,
            "pairs_trades": pairs_trades,
            "hedging_pairs": hedging_pairs,
            "lookback_days": lookback_days,
        }
    except Exception as e:
        logger.error(f"Error calculating correlation matrix: {e}")
        return {"error": str(e), "matrix": [], ...}
```

### correlation_engine.py - Pairs Trade Identification

```python
def _identify_pairs_trades(
    tickers: List[str],
    sectors: List[str],
    corr_matrix: List[List[float]],
) -> List[Dict[str, Any]]:
    """
    Identify pairs trade opportunities:
    - High correlation (>0.7) + diverging RRG quadrants
    - One Strengthening/Recovering, other Weakening/Deteriorating
    - Mean-reversion opportunity
    """
    pairs_trades = []

    try:
        # Get RRG data to check quadrants
        rrg_data = calculate_rrg(tickers)

        # Build RRG quadrant lookup
        rrg_quadrants = {}
        for sector in rrg_data["sectors"]:
            rrg_quadrants[sector["ticker"]] = sector["quadrant"]

        # Find highly correlated pairs with diverging quadrants
        for i, ticker1 in enumerate(tickers):
            for j, ticker2 in enumerate(tickers):
                if i >= j:  # Avoid duplicates
                    continue

                corr = corr_matrix[i][j]

                # High correlation threshold for pairs trades
                if corr > 0.7:
                    quad1 = rrg_quadrants.get(ticker1)
                    quad2 = rrg_quadrants.get(ticker2)

                    if not quad1 or not quad2:
                        continue

                    # Check for divergence
                    strengthening_set = {"Strengthening", "Recovering"}
                    weakening_set = {"Weakening", "Deteriorating"}

                    if (quad1 in strengthening_set and quad2 in weakening_set) or \
                       (quad1 in weakening_set and quad2 in strengthening_set):

                        # Determine trade direction
                        if quad1 in strengthening_set:
                            long_ticker = ticker1
                            short_ticker = ticker2
                        else:
                            long_ticker = ticker2
                            short_ticker = ticker1

                        pairs_trades.append({
                            "ticker1": long_ticker,
                            "ticker2": short_ticker,
                            "correlation": round(corr, 4),
                            "quadrant1": rrg_quadrants[long_ticker],
                            "quadrant2": rrg_quadrants[short_ticker],
                            "conviction": round(min(abs(corr - 0.7) + 0.3, 1.0), 2),
                        })

        # Sort by conviction descending
        pairs_trades.sort(key=lambda x: x["conviction"], reverse=True)

    except Exception as e:
        logger.error(f"Error identifying pairs trades: {e}")

    return pairs_trades
```

### correlation.py - API Endpoints

```python
@router.get("/matrix")
def get_correlation_matrix(lookback: int = Query(90, ge=30, le=365)):
    """
    Get correlation matrix for all sector ETFs.

    Query Parameters:
    - lookback: Number of days (30-365, default 90)

    Returns full matrix with pairs trades and hedging opportunities.
    """
    result = calculate_correlation_matrix(lookback_days=lookback)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "lookback_days": lookback,
        **result,
    }


@router.get("/pair/{ticker1}/{ticker2}")
def get_pair_analysis(
    ticker1: str,
    ticker2: str,
    lookback: int = Query(90, ge=30, le=365)
):
    """
    Get detailed pair analysis: spread, z-score, rolling correlation.
    """
    result = get_pair_details(ticker1, ticker2, lookback_days=lookback)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "lookback_days": lookback,
        **result,
    }
```

## Frontend Examples

### useCorrelation.ts - Type Definitions and Hooks

```typescript
// Type definitions following IntradaySignal pattern (local only)
export interface PairsTrade {
  ticker1: string;
  ticker2: string;
  sector1: string;
  sector2: string;
  correlation: number;
  quadrant1: string;
  quadrant2: string;
  trade_type: string;
  conviction: number;
}

export interface CorrelationData {
  timestamp: string;
  lookback_days: number;
  matrix: number[][];
  tickers: string[];
  sectors: string[];
  pairs_trades: PairsTrade[];
  hedging_pairs: HedgingPair[];
  error?: string;
}

// React Query hooks with 5-minute caching
export function useCorrelationMatrix(lookback: number = 90) {
  return useQuery<CorrelationData, AxiosError>({
    queryKey: ['correlationMatrix', lookback],
    queryFn: async () => {
      const { data } = await axios.get<CorrelationData>(
        `/api/correlation/matrix?lookback=${lookback}`
      );
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function usePairsTrades(lookback: number = 90) {
  return useQuery<
    { timestamp: string; lookback_days: number; pairs_trades: PairsTrade[] },
    AxiosError
  >({
    queryKey: ['pairsTrades', lookback],
    queryFn: async () => {
      const { data } = await axios.get(
        `/api/correlation/pairs?lookback=${lookback}`
      );
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

### CorrelationMatrix.tsx - Heat Map Rendering

```typescript
function getCorrelationColor(value: number): {
  bg: string;
  text: string;
} {
  if (value > 0.8) {
    return { bg: 'bg-green-950', text: 'text-green-300' };
  } else if (value > 0.5) {
    return { bg: 'bg-green-900', text: 'text-green-200' };
  } else if (value > 0) {
    return { bg: 'bg-neutral-700', text: 'text-green-100' };
  } else if (value > -0.3) {
    return { bg: 'bg-neutral-700', text: 'text-neutral-300' };
  } else if (value > -0.5) {
    return { bg: 'bg-red-900', text: 'text-red-200' };
  } else {
    return { bg: 'bg-red-950', text: 'text-red-300' };
  }
}

export function CorrelationMatrix({ data, onPairSelect }: CorrelationMatrixProps) {
  const [hoveredCell, setHoveredCell] = useState<{ i: number; j: number } | null>(null);

  return (
    <div className="overflow-x-auto bg-neutral-900 rounded border border-neutral-800">
      <table className="w-full border-collapse text-xs">
        <tbody>
          {displayMatrix.map((row, i) => (
            <tr key={i}>
              {row.map((corr, j) => {
                const isDiagonal = i === j;
                const colors = getCorrelationColor(corr);

                return (
                  <td
                    key={j}
                    className={`border border-neutral-700 p-1 text-center cursor-pointer transition-all ${
                      isDiagonal ? 'bg-neutral-900 border-neutral-600' : colors.bg
                    }`}
                    onClick={() => {
                      if (!isDiagonal && onPairSelect) {
                        onPairSelect(displayTickers[i], displayTickers[j]);
                      }
                    }}
                  >
                    <span className={`font-semibold ${isDiagonal ? 'text-neutral-500' : colors.text}`}>
                      {isDiagonal ? '1.00' : corr.toFixed(2)}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### PairsPanel.tsx - Pairs Trade Card

```typescript
function getQuadrantBadge(quadrant: string): { bg: string; text: string; label: string } {
  switch (quadrant) {
    case 'Strengthening':
      return { bg: 'bg-green-900', text: 'text-green-100', label: '↗ Strengthening' };
    case 'Weakening':
      return { bg: 'bg-yellow-900', text: 'text-yellow-100', label: '↘ Weakening' };
    case 'Recovering':
      return { bg: 'bg-blue-900', text: 'text-blue-100', label: '↙ Recovering' };
    case 'Deteriorating':
      return { bg: 'bg-red-900', text: 'text-red-100', label: '↖ Deteriorating' };
    default:
      return { bg: 'bg-neutral-800', text: 'text-neutral-300', label: quadrant };
  }
}

// Pairs trade card rendering
{pairsTrades.map((pair, idx) => {
  const quad1 = getQuadrantBadge(pair.quadrant1);
  const quad2 = getQuadrantBadge(pair.quadrant2);

  return (
    <div key={idx} className="border border-neutral-700 rounded p-3 bg-neutral-900">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold text-neutral-100">
          <span className="text-green-400">{pair.ticker1}</span>
          {' / '}
          <span className="text-red-400">{pair.ticker2}</span>
        </div>
        <div className={`text-sm font-semibold ${getConvictionColor(pair.conviction)}`}>
          {(pair.conviction * 100).toFixed(0)}%
        </div>
      </div>

      <div className="flex gap-2 mb-2">
        <span className={`px-2 py-1 rounded text-xs font-medium ${quad1.bg} ${quad1.text}`}>
          {pair.ticker1}: {quad1.label}
        </span>
        <span className={`px-2 py-1 rounded text-xs font-medium ${quad2.bg} ${quad2.text}`}>
          {pair.ticker2}: {quad2.label}
        </span>
      </div>

      <p className="text-xs text-neutral-300 italic">
        <span className="text-green-400">Long {pair.ticker1}</span>
        {' / '}
        <span className="text-red-400">Short {pair.ticker2}</span>
      </p>
    </div>
  );
})}
```

### Correlation.tsx - Page Layout

```typescript
export function Correlation() {
  const [lookback, setLookback] = useState(90);
  const { data, isLoading, error, refetch } = useCorrelationMatrix(lookback);

  const lookbackOptions = [
    { label: '30D', value: 30 },
    { label: '60D', value: 60 },
    { label: '90D', value: 90 },
    { label: '180D', value: 180 },
  ];

  return (
    <div className="p-4 space-y-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-neutral-100">
          Sector Correlation Analysis
        </h1>
        <p className="text-sm text-neutral-400">
          Identify pairs trades and hedging opportunities from cross-sector correlations
        </p>
      </div>

      {/* Lookback Period Selector */}
      <div className="flex items-center gap-2 bg-neutral-900 border border-neutral-800 rounded p-3">
        <span className="text-xs font-medium text-neutral-400">Lookback Period:</span>
        <div className="flex gap-2">
          {lookbackOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setLookback(option.value)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                lookback === option.value
                  ? 'bg-neutral-700 text-neutral-100'
                  : 'text-neutral-400 hover:text-neutral-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Two-Column Layout: 70/30 */}
      {data && (
        <div className="grid gap-4 lg:grid-cols-10">
          <div className="lg:col-span-7">
            <CorrelationMatrix
              data={data}
              onPairSelect={(ticker1, ticker2) =>
                setSelectedPair({ ticker1, ticker2 })
              }
            />
          </div>

          <div className="lg:col-span-3">
            <PairsPanel
              pairsTrades={data.pairs_trades || []}
              hedgingPairs={data.hedging_pairs || []}
              onPairSelect={(ticker1, ticker2) =>
                setSelectedPair({ ticker1, ticker2 })
              }
            />
          </div>
        </div>
      )}
    </div>
  );
}
```

## Key Implementation Patterns

### 1. Error Handling Pattern (Backend)
```python
try:
    # Main logic
    result = calculate_correlation_matrix(lookback_days)
except Exception as e:
    logger.error(f"Error calculating correlation: {e}")
    return {
        "error": str(e),
        "matrix": [],
        # ... default values
    }
```

### 2. React Query Pattern (Frontend)
```typescript
export function useCorrelationMatrix(lookback: number = 90) {
  return useQuery<CorrelationData, AxiosError>({
    queryKey: ['correlationMatrix', lookback],
    queryFn: async () => {
      const { data } = await axios.get<CorrelationData>(
        `/api/correlation/matrix?lookback=${lookback}`
      );
      return data;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}
```

### 3. Tailwind Dark Theme Pattern
```tsx
<div className="bg-neutral-900 border border-neutral-800 rounded p-4">
  <h3 className="text-sm font-semibold text-neutral-100">Title</h3>
  <p className="text-xs text-neutral-400">Description</p>
  <button className="px-3 py-1 bg-neutral-700 text-neutral-100 rounded hover:bg-neutral-600">
    Action
  </button>
</div>
```

### 4. Conditional Styling Pattern
```tsx
<div className={`px-2 py-1 rounded ${
  conviction >= 0.8 ? 'text-green-400' :
  conviction >= 0.6 ? 'text-lime-400' :
  conviction >= 0.4 ? 'text-yellow-400' :
  'text-neutral-400'
}`}>
  {conviction}
</div>
```

## Testing Examples

### API Test
```bash
# Get correlation matrix (90-day lookback)
curl -X GET "http://localhost:8000/api/correlation/matrix?lookback=90"

# Get pairs trades (60-day lookback)
curl -X GET "http://localhost:8000/api/correlation/pairs?lookback=60"

# Get pair details
curl -X GET "http://localhost:8000/api/correlation/pair/XLK/XLV?lookback=90"
```

### React Testing (using React Testing Library)
```typescript
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Correlation } from './Correlation';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

test('renders correlation page', () => {
  render(
    <QueryClientProvider client={queryClient}>
      <Correlation />
    </QueryClientProvider>
  );

  expect(screen.getByText(/Sector Correlation Analysis/i)).toBeInTheDocument();
  expect(screen.getByText(/30D/)).toBeInTheDocument();
  expect(screen.getByText(/90D/)).toBeInTheDocument();
});
```

## Summary

These code examples demonstrate:
- Proper error handling with logging
- Type-safe implementations
- React Query best practices
- Tailwind v4 dark theme consistency
- Clean component architecture
- API design principles
