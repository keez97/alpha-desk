# Step 5: Event Scanner Backend Implementation

## Files Created (5 files, ~1,974 lines)
- `backend/services/event_producer.py` — EventProducerService: SEC EDGAR RSS parsing (8-K, 10-K, 10-Q, Form 4, SC 13D/G), yfinance calendar scraping, rate limiting (10 req/sec), ticker-to-CIK mapping.
- `backend/services/event_processor.py` — EventProcessingEngine: 30+ event type classification, severity scoring (1-5), alpha decay calculation (1d/5d/21d/63d windows), full pipeline orchestration.
- `backend/services/event_consumer.py` — EventConsumerService: Factor signal generation (-1 to +1), screener badge updates, event correlation analysis. 5 factor types: insider_sentiment, earnings_surprise, activist_involvement, dividend_yield, corporate_action.
- `backend/services/event_polling.py` — BackgroundPollingService: Thread-safe polling orchestration, status tracking, error logging.
- `backend/routers/events.py` — 8 REST endpoints under /api/events: list, detail, alpha-decay, scan, polling-status, timeline, screener-badges, delete. Pydantic models for all requests/responses.

## Files Modified
- `backend/main.py` — Added events router
