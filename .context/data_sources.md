# AlphaDesk — Data Sources

## Yahoo Finance (yfinance)
- **Library:** `yfinance` Python package
- **No API key required**
- **Rate limits:** Unofficial, ~2000 requests/hour. Use exponential backoff.
- **Used for:**
  - Real-time quotes: `yf.Ticker(symbol).info`
  - Price history: `yf.Ticker(symbol).history(period, interval)`
  - Ticker search: `yf.Ticker(symbol).info` (validate existence)
  - Short interest: `yf.Ticker(symbol).info['shortPercentOfFloat']`
  - Options data: `yf.Ticker(symbol).options`

### Key Tickers
- **Sector ETFs:** XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLB, XLU, XLRE, XLC
- **Macro:** ^TNX (10Y), ^IRX (2Y proxy), ^VIX, DX-Y.NYB (DXY), GC=F (Gold), CL=F (WTI), BTC-USD
- **Indices:** SPY, QQQ, IWM, ^GDAXI (DAX), ^FTSE, ^N225 (Nikkei), EEM
- **Credit:** HYG, LQD

## financialdatasets.ai
- **Base URL:** `https://api.financialdatasets.ai`
- **Auth:** Header `X-API-KEY: <key>`
- **Used for:** income statements, balance sheets, cash flow, financial ratios, institutional ownership
- **Key endpoints (check docs for exact paths):**
  - `/financials/income-statements?ticker={ticker}`
  - `/financials/balance-sheets?ticker={ticker}`
  - `/financials/cash-flow-statements?ticker={ticker}`

## Claude API (Anthropic)
- **Model:** `claude-sonnet-4-20250514`
- **Tools:** `web_search_20250305` (for morning brief, weekly report, screener)
- **Streaming:** Used for weekly report generation (SSE)
- **All calls include base analyst persona as system prompt**
