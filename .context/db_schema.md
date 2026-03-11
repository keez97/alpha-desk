# AlphaDesk — Data Persistence

> **Last updated:** 2026-03-11

## Caching Architecture
AlphaDesk uses two tiers of caching:

### In-Memory TTLCache (Primary for real-time data)
Most real-time market data is cached in-memory using a custom `TTLCache` class (`backend/services/cache.py`). This provides sub-millisecond reads with automatic expiration.

| Service | Cache Key Pattern | TTL | Notes |
|---------|------------------|-----|-------|
| Macro data | `macro_data` | 5 min | Quotes, indices, commodities |
| Sector data | `sector_data_{period}` | 5 min | ETF prices by period |
| VIX term structure | `vix_term` | 5 min | CBOE futures data |
| Market breadth | `breadth` | 5 min | S&P 100 advancing/declining |
| Scenario risk | `scenario_risk_fast` | 30 min | Stress scenario calculations |
| COT positioning | `cot_data` | 1 hour | CFTC Commitment of Traders |
| Overnight returns | Date-seeded | Daily | Synthetic estimates stable per day |

### SQLite via SQLModel (Persistence for generated content)
Longer-lived content that should survive server restarts is stored in SQLite.

## SQLite Tables

### watchlist
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, AUTOINCREMENT |
| ticker | TEXT | UNIQUE, NOT NULL |
| added_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| last_grade | TEXT | Nullable, cached JSON |
| last_grade_at | TIMESTAMP | Nullable |

### portfolio
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, AUTOINCREMENT |
| name | TEXT | NOT NULL |
| capital | REAL | NOT NULL, DEFAULT 100000 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### portfolio_holding
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, AUTOINCREMENT |
| portfolio_id | INTEGER | FK → portfolio(id) ON DELETE CASCADE |
| ticker | TEXT | NOT NULL |
| weight | REAL | Nullable |
| — | — | UNIQUE(portfolio_id, ticker) |

### weekly_report
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, AUTOINCREMENT |
| generated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| data_as_of | TEXT | |
| report_json | TEXT | NOT NULL |
| summary | TEXT | Nullable |

### morning_brief_cache
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, AUTOINCREMENT |
| cache_key | TEXT | UNIQUE, NOT NULL |
| data_json | TEXT | NOT NULL |
| generated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| expires_at | TIMESTAMP | |

### stock_grade_cache
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, AUTOINCREMENT |
| ticker | TEXT | NOT NULL |
| grade_json | TEXT | NOT NULL |
| generated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### screener_cache
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, AUTOINCREMENT |
| screen_type | TEXT | NOT NULL |
| results_json | TEXT | NOT NULL |
| generated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

## Notes
- SQLite is sufficient for single-user deployment; schema designed for easy PostgreSQL migration if needed
- In-memory caches are lost on Railway redeploy/restart — first request after restart will be slower
- The `morning_brief_cache` SQLite table is used for AI-generated morning drivers (4-hour TTL), separate from the in-memory real-time data caches
