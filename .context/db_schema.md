# AlphaDesk — Database Schema

## Engine
SQLite via SQLModel (Pydantic + SQLAlchemy)

## Tables

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
