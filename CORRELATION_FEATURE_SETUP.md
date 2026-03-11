# Correlation Heat Map Feature - Integration Guide

## Overview
The Correlation Heat Map feature provides cross-sector correlation analysis to identify pairs trades and hedging opportunities. This document outlines the implementation and required integration steps.

## Files Created

### Backend
- `/backend/services/correlation_engine.py` - Core correlation calculation engine
- `/backend/routers/correlation.py` - FastAPI router endpoints

### Frontend
- `/frontend/src/hooks/useCorrelation.ts` - React query hooks for data fetching
- `/frontend/src/components/correlation/CorrelationMatrix.tsx` - Heat map visualization
- `/frontend/src/components/correlation/PairsPanel.tsx` - Pairs trades & hedging panel
- `/frontend/src/pages/Correlation.tsx` - Main page component

## Integration Steps

### 1. Backend Router Registration

Edit `/backend/main.py`:

```python
# Add to imports section (around line 5-25):
from backend.routers import (
    # ... existing imports ...
    correlation,  # ADD THIS LINE
)

# Add to router registration section (around line 42-61):
app.include_router(correlation.router)  # ADD THIS LINE
```

### 2. Frontend Route Registration

Edit `/frontend/src/App.tsx`:

```typescript
// Add to imports (around line 1-13):
import { Correlation } from './pages/Correlation';  // ADD THIS LINE

// Add to Routes section (around line 28-39):
<Route path="/correlation" element={<Correlation />} />  // ADD THIS LINE
```

### 3. Navigation Menu (Optional)

To add the Correlation page to the navigation menu, update the navigation component that displays the menu items. Look for a component like `AppShell.tsx` or `Sidebar.tsx` and add:

```typescript
{ label: 'Correlation', path: '/correlation', icon: 'ChartNetwork' }
```

## API Endpoints

The following endpoints are available once the router is registered:

### GET /api/correlation/matrix
Get correlation matrix for all sector ETFs.

**Query Parameters:**
- `lookback` (int): Number of days (30-365, default 90)

**Response:**
```json
{
  "timestamp": "2024-03-10T12:00:00.000000",
  "lookback_days": 90,
  "matrix": [[1.0, 0.72, ...], ...],
  "tickers": ["XLK", "XLV", ...],
  "sectors": ["Information Technology", "Healthcare", ...],
  "pairs_trades": [...],
  "hedging_pairs": [...]
}
```

### GET /api/correlation/pairs
Get identified pairs trade opportunities only.

**Query Parameters:**
- `lookback` (int): Number of days (30-365, default 90)

### GET /api/correlation/pair/{ticker1}/{ticker2}
Get detailed pair analysis with spread metrics.

**Query Parameters:**
- `lookback` (int): Number of days (30-365, default 90)

**Response:**
```json
{
  "timestamp": "2024-03-10T12:00:00.000000",
  "lookback_days": 90,
  "ticker1": "XLK",
  "ticker2": "XLV",
  "current_spread": 2.45,
  "spread_mean": 1.23,
  "spread_std": 3.21,
  "z_score": 0.38,
  "rolling_correlation_20d": 0.68,
  "overall_correlation": 0.72,
  "spread_history": [...]
}
```

## Feature Details

### Correlation Matrix
- Full cross-sector correlation heatmap
- Color-coded cells (green=positive, red=negative)
- Interactive hover tooltips
- Configurable lookback periods: 30D, 60D, 90D, 180D

### Pairs Trades
- Identifies mean-reversion opportunities
- Criteria: correlation > 0.7 with diverging RRG quadrants
- Surfaces one sector strengthening while other deteriorates
- Conviction score based on correlation strength and quadrant divergence
- Sorted by conviction level

### Hedging Pairs
- Identifies diversification opportunities
- Criteria: correlation < -0.3 (negative) or near 0 (low)
- Two types: "Negative" (inverse relationship) and "Low" (low correlation)

## Technical Details

### Correlation Calculation
- Uses 90-day (or custom) daily close prices
- Calculates daily returns using percentage change
- Computes Pearson correlation matrix on returns
- Aligned with yfinance data

### RRG Quadrant Integration
- Leverages existing RRG calculations
- Maps to 4 quadrants: Strengthening, Weakening, Recovering, Deteriorating
- Identifies divergence for mean-reversion pairs

### Performance
- Matrix: ~50ms for 10 tickers with 90-day lookback
- Caching: 5-minute stale time on React Query
- Handles missing data gracefully with fallbacks

## Dependencies

### Backend
- `pandas` - Data manipulation
- `numpy` - Correlation calculations
- `yfinance` - Historical price data (via yfinance_service)
- `fastapi` - API framework

### Frontend
- `@tanstack/react-query` - Data fetching & caching
- `axios` - HTTP client
- `react` - UI framework
- `tailwindcss` - Styling (v4)

## Testing

### Manual Testing
1. Navigate to `/correlation` route
2. Verify correlation matrix loads with color coding
3. Click on matrix cells to highlight
4. Test lookback period buttons (30D, 60D, 90D, 180D)
5. Verify pairs trades display mean-reversion opportunities
6. Verify hedging pairs show low/negative correlation pairs

### API Testing
```bash
# Get correlation matrix
curl "http://localhost:5173/api/correlation/matrix?lookback=90"

# Get pairs trades
curl "http://localhost:5173/api/correlation/pairs?lookback=90"

# Get pair details
curl "http://localhost:5173/api/correlation/pair/XLK/XLV?lookback=90"
```

## Styling

All components follow the dark theme pattern used throughout AlphaDesk:
- Background: `bg-[#0a0a0a]`, `bg-neutral-900/800`
- Text: `text-neutral-100/300/400/500`
- Borders: `border-neutral-800/700`
- Accent colors: `text-green-400`, `text-red-400`, `text-blue-400`

## Tailwind v4 Notes

All components use Tailwind v4 utilities and color schemes that match the existing app. No custom CSS files are created.

## Future Enhancements

1. **Pair Spread Visualization**: Add line chart for spread history
2. **Z-Score Alerts**: Highlight pairs with extreme z-scores
3. **Dynamic Rebalancing**: Suggest rebalancing based on pair performance
4. **Correlation History**: Track correlation strength changes over time
5. **Sector Filtering**: Filter correlation matrix by specific sectors
6. **Export**: Download correlation matrix as CSV
7. **Custom Baskets**: Define custom sector groupings for analysis

## Troubleshooting

### "No correlation data available"
- Verify yfinance can fetch sector ETF data
- Check internet connectivity
- Ensure lookback period doesn't exceed available history

### Pairs trades not appearing
- May require minimum correlation threshold > 0.7
- RRG data must show quadrant divergence
- Check that current RRG calculations are working

### High latency
- First request may take longer while caching
- Subsequent requests within 5 minutes use cached data
- Consider reducing lookback period if needed

## Code Structure

### correlation_engine.py
- `calculate_correlation_matrix()` - Main calculation function
- `_identify_pairs_trades()` - Pairs trade logic
- `_identify_hedging_pairs()` - Hedging logic
- `get_pair_details()` - Detailed pair analysis

### correlation.py
- `/matrix` - GET endpoint for full correlation matrix
- `/pairs` - GET endpoint for pairs trades
- `/pair/{ticker1}/{ticker2}` - GET endpoint for pair details

### useCorrelation.ts
- `useCorrelationMatrix()` - Hook for matrix data
- `usePairsTrades()` - Hook for pairs trades
- `usePairDetails()` - Hook for pair analysis details

### CorrelationMatrix.tsx
- Table-based visualization with color coding
- Interactive hover tooltips
- Legend for color interpretation

### PairsPanel.tsx
- Pairs trades card list
- Hedging pairs card list
- RRG quadrant badges
- Conviction scores

### Correlation.tsx
- Main page layout (70/30 split)
- Lookback period selector
- Error and loading states
- Selected pair detail view

## Integration Checklist

- [ ] Register correlation router in main.py
- [ ] Add Correlation route to App.tsx
- [ ] (Optional) Add navigation menu item
- [ ] (Optional) Update any README/documentation files
- [ ] Test API endpoints
- [ ] Test frontend page loading
- [ ] Verify heat map colors
- [ ] Test pairs trades identification
- [ ] Test hedging pairs identification
- [ ] Test lookback period selector
- [ ] Verify dark theme styling

## Contact

For questions or issues with the Correlation Heat Map feature, refer to the implementation files which include detailed comments and error handling.
