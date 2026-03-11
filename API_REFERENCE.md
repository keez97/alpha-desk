# AlphaDesk Event Scanner API Reference

Base URL: `/api/events`

## Endpoints

### 1. List Events (Paginated, Filterable)
```http
GET /api/events
```

Query Parameters:
- `ticker` (string, optional): Filter by ticker symbol
- `event_type` (string, optional): Filter by event type (e.g., "insider_trade_buy_large")
- `severity_min` (integer, optional): Minimum severity 1-5
- `severity_max` (integer, optional): Maximum severity 1-5
- `start_date` (date, optional): Event date start (YYYY-MM-DD)
- `end_date` (date, optional): Event date end (YYYY-MM-DD)
- `source` (string, optional): Filter by source (SEC_EDGAR, YFINANCE)
- `limit` (integer, default 50): Results per page (1-500)
- `offset` (integer, default 0): Results to skip

Response:
```json
{
  "items": [
    {
      "event_id": 123,
      "ticker": "AAPL",
      "event_type": "insider_trade_buy_large",
      "severity_score": 4,
      "detected_at": "2024-03-10T10:30:00Z",
      "event_date": "2024-03-09",
      "headline": "Form 4 filing: CEO bought 100,000 shares",
      "source": "SEC_EDGAR"
    }
  ],
  "total": 450,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

---

### 2. Get Event Details with Alpha Decay
```http
GET /api/events/{event_id}
```

Path Parameters:
- `event_id` (integer): Event ID

Response:
```json
{
  "event_id": 123,
  "ticker": "AAPL",
  "event_type": "insider_trade_buy_large",
  "severity_score": 4,
  "detected_at": "2024-03-10T10:30:00Z",
  "event_date": "2024-03-09",
  "source": "SEC_EDGAR",
  "headline": "Form 4 filing: CEO bought 100,000 shares",
  "description": null,
  "metadata": {
    "transaction_type": "buy",
    "transaction_size": "large",
    "source": "SEC_EDGAR"
  },
  "created_at": "2024-03-10T10:30:00Z",
  "alpha_decay_windows": [
    {
      "window_id": 456,
      "event_id": 123,
      "window_type": "1d",
      "abnormal_return": 0.0234,
      "benchmark_return": 0.0012,
      "measured_at": "2024-03-10T10:30:00Z",
      "confidence": 1.0,
      "sample_size": 1
    },
    {
      "window_id": 457,
      "event_id": 123,
      "window_type": "5d",
      "abnormal_return": 0.0567,
      "benchmark_return": 0.0089,
      "measured_at": "2024-03-10T10:30:00Z",
      "confidence": 1.0,
      "sample_size": 1
    }
  ]
}
```

---

### 3. Get Alpha Decay Windows
```http
GET /api/events/{event_id}/alpha-decay
```

Path Parameters:
- `event_id` (integer): Event ID

Query Parameters:
- `window_type` (string, optional): Filter by window (1d, 5d, 21d, 63d)

Response: Array of AlphaDecayResponse objects

---

### 4. Trigger Manual Scan (Background)
```http
POST /api/events/scan
```

Query Parameters:
- `tickers` (list of strings, optional): Specific tickers to scan (e.g., ?tickers=AAPL&tickers=MSFT)

Response:
```json
{
  "message": "Event scan triggered in background",
  "task_id": null,
  "status": "queued"
}
```

---

### 5. Get Polling Service Status
```http
GET /api/events/polling-status
```

Response:
```json
{
  "status": "completed_success",
  "last_run": "2024-03-10T10:30:00Z",
  "next_run_estimate": "2024-03-10T11:30:00Z",
  "polling_interval_hours": 1,
  "events_found": 23,
  "errors": []
}
```

---

### 6. Get Event Timeline (Watchlist)
```http
GET /api/events/timeline
```

Query Parameters:
- `days_back` (integer, default 30): Days to look back (1-365)
- `ticker` (string, optional): Filter by specific ticker
- `event_type` (string, optional): Filter by event type
- `min_severity` (integer, default 1): Minimum severity (1-5)
- `limit` (integer, default 100): Results per page
- `offset` (integer, default 0): Results to skip

Response:
```json
{
  "items": [
    {
      "event_id": 123,
      "ticker": "AAPL",
      "event_type": "insider_trade_buy_large",
      "severity_score": 4,
      "headline": "Form 4 filing: CEO bought 100,000 shares",
      "detected_at": "2024-03-10T10:30:00Z",
      "event_date": "2024-03-09"
    }
  ],
  "total": 127,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

---

### 7. Get Screener Badges (Batch)
```http
GET /api/events/screener-badges
```

Query Parameters:
- `tickers` (list of strings): Tickers to get badges for (repeat: ?tickers=AAPL&tickers=MSFT)
- `lookback_days` (integer, default 30): Days to look back for recent events

Response:
```json
{
  "badges": [
    {
      "ticker": "AAPL",
      "max_severity": 4,
      "recent_event_count": 3,
      "event_types": [
        "insider_trade_buy_large",
        "earnings_announcement",
        "dividend_ex_date"
      ],
      "latest_event": "insider_trade_buy_large (severity 4)"
    },
    {
      "ticker": "MSFT",
      "max_severity": 2,
      "recent_event_count": 1,
      "event_types": ["sec_filing_10q"],
      "latest_event": "sec_filing_10q (severity 2)"
    }
  ],
  "timestamp": "2024-03-10T10:30:00Z"
}
```

---

### 8. Delete Event
```http
DELETE /api/events/{event_id}
```

Path Parameters:
- `event_id` (integer): Event ID to delete

Response:
```json
{
  "message": "Event 123 deleted successfully"
}
```

---

## Event Types Reference

### Severity Score Mapping

| Severity | Events | Examples |
|----------|--------|----------|
| 5 | Bankruptcy/Material M&A | 8-K Item 1.01 (Bankruptcy), Item 2.01 (Bankruptcy costs) |
| 4 | Large insider trades, Activist ownership | Form 4 large buy/sell, SC 13D (>5% ownership) |
| 3 | Earnings announcements, Regular insider trades | Earnings date, Form 4 regular buy/sell |
| 2 | Routine SEC filings, Small insider trades | 10-K, 10-Q, Form 4 small transactions |
| 1 | Dividend dates, Passive beneficial ownership | Ex-dividend date, SC 13G (<5% passive) |

### Event Type Codes

- `sec_filing_8k_item_*` - 8-K filing with specific item (1.01, 2.01, etc.)
- `sec_filing_10k` - Annual report
- `sec_filing_10q` - Quarterly report
- `insider_trade_buy_large` - Form 4: Large insider purchase
- `insider_trade_buy_small` - Form 4: Small insider purchase
- `insider_trade_sell_large` - Form 4: Large insider sale
- `insider_trade_sell_small` - Form 4: Small insider sale
- `beneficial_ownership_13d` - Schedule 13D (activist ownership)
- `beneficial_ownership_13g` - Schedule 13G (passive ownership)
- `earnings_announcement` - Earnings announcement date
- `dividend_ex_date` - Dividend ex-date
- `dividend_change_significant` - Significant dividend change

---

## Alpha Decay Windows

Each event includes abnormal returns calculated over 4 time periods:

- **1d**: 1-day abnormal return (immediate market reaction)
- **5d**: 5-day abnormal return (first trading week)
- **21d**: 21-day (trading month) abnormal return
- **63d**: 63-day (trading quarter) abnormal return

Formula:
```
abnormal_return = (security_return - benchmark_return)
```

Where:
- `security_return = (price[t+window] / price[t]) - 1`
- `benchmark_return = (SPY[t+window] / SPY[t]) - 1`
- `t` = event date
- `window` = window length in days

---

## Filtering Examples

### Get high-severity insider trades in last 90 days
```
GET /api/events?event_type=insider_trade_buy_large&severity_min=4&days_back=90
```

### Get all 8-K filings for AAPL
```
GET /api/events?ticker=AAPL&event_type=sec_filing_8k
```

### Get events by date range
```
GET /api/events?start_date=2024-01-01&end_date=2024-03-10
```

### Get only SEC EDGAR events
```
GET /api/events?source=SEC_EDGAR&limit=100
```

---

## Error Responses

All errors follow standard HTTP status codes:

- `400 Bad Request`: Invalid query parameters
- `404 Not Found`: Event ID not found
- `500 Internal Server Error`: Server error (check logs)

Error Response Format:
```json
{
  "detail": "Event 999 not found"
}
```

---

## Rate Limits

- No per-client rate limiting on API endpoints
- SEC EDGAR scanning: 10 requests/second (internal, not user-facing)
- Batch screener badges: up to 100 tickers per request

---

## Authentication

Currently: No authentication required (development mode)
Future: Add API key or OAuth2 authentication

---

## Pagination

All list endpoints support cursor-based pagination:

```
GET /api/events?limit=50&offset=0
```

Use `has_more` field to detect end of results:
```json
{
  "items": [...],
  "total": 450,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

Next page:
```
GET /api/events?limit=50&offset=50
```

---

## Background Scan Details

Polling cycle executes 3 CEP layers:

**Layer 1: Event Producer**
- Scans SEC EDGAR for recent filings
- Scans yfinance for earnings/dividend dates
- Returns: raw event dictionaries

**Layer 2: Event Processor**
- Classifies events (30+ types)
- Scores severity (1-5)
- Calculates alpha decay windows (1d, 5d, 21d, 63d)
- Saves Event + AlphaDecayWindow records

**Layer 3: Event Consumer**
- Generates factor signals
- Updates screener badges
- Analyzes event correlations

Total typical runtime: 5-30 seconds depending on watchlist size and network conditions.

---

## Examples

### Python Example: List AAPL Insider Trades
```python
import requests

url = "http://localhost:8000/api/events"
params = {
    "ticker": "AAPL",
    "event_type": "insider_trade_buy_large",
    "limit": 10
}

response = requests.get(url, params=params)
events = response.json()

for event in events["items"]:
    print(f"{event['detected_at']}: {event['headline']} (severity {event['severity_score']})")
```

### cURL Example: Trigger Scan
```bash
curl -X POST "http://localhost:8000/api/events/scan?tickers=AAPL&tickers=MSFT"
```

### cURL Example: Get Timeline
```bash
curl "http://localhost:8000/api/events/timeline?days_back=30&min_severity=3"
```

---

## FAQ

**Q: How often does polling run?**
A: Default is every 1 hour. Can be triggered manually via POST /api/events/scan.

**Q: What is abnormal_return?**
A: The security's return minus the benchmark (SPY) return over a time window. Positive = outperformance.

**Q: How are alpha decay windows calculated?**
A: Using PiT (point-in-time) safe price queries to ensure only data available at event date is used.

**Q: Can I filter by multiple event types?**
A: Currently no. Make multiple requests or use the timeline endpoint.

**Q: What's the difference between detected_at and event_date?**
A: `event_date` = when the event occurred (e.g., 8-K filing date)
   `detected_at` = when AlphaDesk found it (usually same day or next trading day)

**Q: Can I subscribe to notifications?**
A: Not yet. Use polling-status endpoint to check for new events.

