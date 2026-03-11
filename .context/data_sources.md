# AlphaDesk — Data Sources

## Data Tier Hierarchy
The system uses a multi-tier data cascade. Higher tiers are tried first; lower tiers serve as fallbacks.

### Tier 1: financialdatasets.ai (FDS)
- **Library:** Custom `fds_client.py`
- **Base URL:** `https://api.financialdatasets.ai`
- **Auth:** Header `X-API-KEY` from env `FDS_API_KEY`
- **Used for:** Income statements, balance sheets, cash flow, financial ratios, institutional ownership
- **Key endpoints:**
  - `/financials/income-statements?ticker={ticker}`
  - `/financials/balance-sheets?ticker={ticker}`
  - `/financials/cash-flow-statements?ticker={ticker}`

### Tier 2: FRED (Federal Reserve Economic Data)
- **Library:** Custom `fred_client.py` and `fred_service.py`
- **Auth:** Query param `api_key` from env `FRED_API_KEY`
- **Used for:** VIX, yield curve data, macro indicators, fear & greed proxy
- **Key series:** VIXCLS (VIX close), DGS10 (10Y yield), DGS2 (2Y yield), DFF (fed funds rate)
- **Also used by:** Synthetic estimator for VIX-based overnight gap estimation

### Tier 3: Yahoo Finance (yfinance)
- **Library:** `yfinance` Python package + custom `yfinance_service.py`
- **No API key required**
- **Rate limits:** Unofficial, ~2000 requests/hour. Uses exponential backoff.
- **Used for:**
  - Real-time quotes: `yf.Ticker(symbol).info`
  - Price history: `yf.Ticker(symbol).history(period, interval)`
  - Options data: `yf.Ticker(symbol).options`
  - Sector ETF performance
  - Market breadth (S&P 100 component prices)

### Tier 4: Synthetic Estimator
- **Library:** `synthetic_estimator.py` — no external dependencies, uses FRED data only
- **No API key required** (uses cached FRED data)
- **Used when:** All live sources fail or timeout
- **Provides:**
  - Overnight return estimates (VIX-implied volatility scaling with beta multipliers)
  - Options flow estimates (VIX regime → IV skew, put/call ratio, GEX)
  - Cross-asset momentum estimates (FRED yield curve, VIX → asset class momentum)

## Other Data Sources

### Stooq
- **Library:** Custom `stooq_service.py`
- **No API key required**
- **Used for:** International index data when yfinance fails
- **Tickers:** DAX, FTSE, Nikkei, Hang Seng, ASX

### CBOE (Chicago Board Options Exchange)
- **Library:** Custom `vix_central_service.py` + `cboe_service.py`
- **No API key required** (public data scraping)
- **Used for:** VIX futures term structure data (spot, 3M, contango/backwardation)

### CNN Fear & Greed Index
- **Library:** Custom `cnn_fear_greed.py`
- **No API key required** (public API)
- **Used for:** Market sentiment indicator (0-100 scale)

### Claude AI (via OpenRouter)
- **Library:** `claude_service.py` using OpenRouter API
- **Auth:** `OPENROUTER_API_KEY` in env
- **Model:** `claude-sonnet-4` (OpenRouter model ID: `anthropic/claude-sonnet-4`)
- **Tools:** `web_search` for real-time market data in AI analysis
- **Used for:**
  - Morning Brief market drivers (AI-generated with web search)
  - Weekly market report (SSE streaming)
  - Stock grading (AI-powered A-F grades with metrics)
  - Morning Report narrative (generated from panel data)

## Key Tickers

### Sector ETFs (11)
XLK (Tech), XLF (Financials), XLE (Energy), XLV (Healthcare), XLY (Consumer Disc.), XLP (Consumer Staples), XLI (Industrials), XLB (Materials), XLU (Utilities), XLRE (Real Estate), XLC (Communication)

### Macro Indicators
^TNX (10Y yield), ^IRX (3M yield), ^VIX (volatility), DX-Y.NYB (Dollar Index), GC=F (Gold), CL=F (WTI Crude), BTC-USD (Bitcoin)

### Major Indices (tracked for overnight gaps)
SPY, QQQ, IWM, DIA + all 10 sector ETFs (XLK, XLV, XLF, XLY, XLP, XLE, XLRE, XLI, XLU, XLC)

### Credit Spreads
HYG (High Yield), LQD (Investment Grade)

### International Indices
^GDAXI (DAX), ^FTSE (FTSE 100), ^N225 (Nikkei), EEM (Emerging Markets)

## Data Source Constraints

| Source | Constraint | Workaround |
|--------|-----------|------------|
| yfinance | Unofficial API, can rate-limit | Exponential backoff, FRED fallback |
| RSS feeds | Blocked from Railway cloud IPs | Synthetic headline generation from market data |
| FDS | API key required, limited free tier | FRED and yfinance as fallbacks |
| FRED | 120 requests/min rate limit | In-memory caching with 5-min TTL |
| CBOE | Public data, scraping may break | VIX fallback from FRED VIXCLS series |
| Stooq | Occasional outages | yfinance fallback for international data |
