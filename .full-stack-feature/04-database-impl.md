# Step 4: Event Scanner Database Implementation

## Files Created
- `backend/models/events.py` — 7 SQLModel classes: Event, EventClassificationRule, AlphaDecayWindow, EventFactorBridge, EventSourceMapping, EventAlertConfiguration, EventCorrelationAnalysis. Enums: EventType (8 types), EventSource, WindowType.
- `backend/repositories/event_repo.py` — EventRepository with 24 methods: CRUD, timeline queries, alpha decay, factor signals, classification rules, alerts, correlations.
- `alembic/versions/002_event_scanner_tables.py` — Migration creating all 7 tables with FKs, unique constraints, composite indexes.

## Files Modified
- `backend/models/__init__.py` — Imported all event models
- `backend/repositories/pit_queries.py` — Added get_events_pit() for PiT-safe event queries
