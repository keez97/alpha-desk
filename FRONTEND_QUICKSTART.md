# AlphaDesk Frontend - Quick Start Guide

## Installation & Setup

### 1. Navigate to the frontend directory
```bash
cd "/sessions/sleepy-charming-ramanujan/mnt/Claude Cowork/alpha-desk/frontend"
```

### 2. Install dependencies (if not already done)
```bash
npm install
```

### 3. Start the development server
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Building for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

## Features & Pages

### 1. **Morning Brief** (Default Page: `/`)
- Macro indicators bar (real-time updates every 5 minutes)
- Sector performance table with multi-period toggle
- Sector performance chart (normalized to 100)
- AI-generated market drivers with refresh capability

### 2. **Stock Screener** (`/screener`)
- Debounced search bar for ticker lookup
- Stock grading with comprehensive metrics
- Expandable sections: Summary, Risks, Catalysts
- Watchlist management sidebar
- Screener results in two tabs:
  - Value Opportunities (companies with low valuations)
  - Momentum Leaders (companies with strong momentum)

### 3. **Weekly Report** (`/weekly-report`)
- Generate AI-powered market analysis reports
- Real-time SSE streaming with progress indication
- View past reports with full history
- Delete old reports
- Collapsible sections for easy navigation

### 4. **Portfolio** (`/portfolio`)
- Create and manage investment portfolios
- Add holdings with share quantities
- View portfolio statistics:
  - Correlation heatmap between holdings
  - Max Sharpe ratio portfolio optimization
  - Minimum variance portfolio optimization
  - Monte Carlo simulation results with percentile bands
- Delete portfolios

### 5. **RRG - Relative Rotation Graph** (`/rrg`)
- Select benchmark ticker (SPY, QQQ, IWM, DIA, or custom)
- Choose time period (3M, 6M, 1Y, 2Y)
- View sector rotation in 4 quadrants:
  - **Leading** (green): Strong and getting stronger
  - **Weakening** (amber): Strong but losing momentum
  - **Lagging** (red): Weak and getting weaker
  - **Improving** (blue): Weak but gaining momentum
- Bubble size represents trading volume

## API Configuration

The development server automatically proxies `/api/*` requests to `http://localhost:8000`.

Make sure your backend API is running before starting the frontend!

## Key Dependencies

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **React Query** - Server state management
- **Zustand** - Client state management
- **Axios** - HTTP client
- **React Router** - Page routing
- **Recharts** - React charting library
- **Plotly.js** - Advanced visualization
- **Framer Motion** - Animation library

## Development Tips

### Hot Module Replacement (HMR)
Changes to React components will automatically reload without losing state.

### Type Checking
The project uses strict TypeScript. All files are fully typed.

### Dark Theme
Everything is styled with a dark theme using Tailwind CSS and custom color tokens.

### Responsive Design
The application is fully responsive and works on mobile, tablet, and desktop.

## Troubleshooting

### Issue: API calls failing
- **Solution**: Ensure backend is running on `http://localhost:8000`
- Check browser DevTools Network tab to verify proxy is working

### Issue: Styles not appearing
- **Solution**: Run `npm install` to ensure all dependencies are installed
- Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)

### Issue: Build errors
- **Solution**: Run `npm install` to update dependencies
- Delete `node_modules` folder and `package-lock.json`, then run `npm install` again

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx                    # Main app with router setup
│   ├── main.tsx                   # Entry point
│   ├── styles/
│   │   ├── globals.css            # Tailwind imports and theme
│   │   └── tokens.ts              # Color constants
│   ├── lib/
│   │   ├── api.ts                 # API client with typed functions
│   │   └── utils.ts               # Utility functions
│   ├── stores/                    # Zustand state management
│   ├── hooks/                     # React Query hooks for data fetching
│   ├── components/
│   │   ├── layout/                # Top nav, sidebar, shell
│   │   ├── shared/                # Reusable UI components
│   │   ├── morning-brief/         # Morning brief page components
│   │   ├── screener/              # Stock screener components
│   │   ├── weekly-report/         # Report components
│   │   ├── portfolio/             # Portfolio analysis components
│   │   └── rrg/                   # RRG chart components
│   └── pages/                     # Full page components
├── vite.config.ts                 # Vite configuration with proxy
├── tsconfig.app.json              # TypeScript config
├── package.json                   # Dependencies
└── index.html                     # HTML template
```

## Performance Notes

- Macro data refreshes every 5 minutes
- Quotes cache for 1 minute
- Sector data caches for 5 minutes
- Tables are sortable for better UX
- Charts use responsive containers
- Images and heavy libraries are loaded on demand

## Security Notes

- All API calls go through the proxy (no CORS issues)
- Type-safe API client prevents runtime errors
- React Query handles caching and invalidation
- No sensitive data stored in localStorage
- All inputs are sanitized through TypeScript

## Next Steps

1. Ensure the backend API is running on `http://localhost:8000`
2. Run `npm run dev` in the frontend directory
3. Open `http://localhost:5173` in your browser
4. Start using AlphaDesk!

## Questions?

Refer to the `FRONTEND_SUMMARY.md` for detailed documentation of all components and features.
