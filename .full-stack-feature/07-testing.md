# Testing & Validation: Factor Backtester

## Test Suite (Step 7a)

### Files Created
- `backend/tests/conftest.py` — In-memory SQLite fixtures (9 fixtures: session, test_client, sample data)
- `backend/tests/test_statistics_calculator.py` — 44+ test cases for all 8 performance metrics + edge cases
- `backend/tests/test_backtest_engine.py` — 40+ test cases: rebalance dates, portfolio construction, turnover, PiT enforcement
- `backend/tests/test_factor_calculator.py` — 30+ test cases: ranking, custom factors, FF exposures
- `backend/tests/test_pit_queries.py` — 50+ test cases: PiT price/fundamental queries, universe filtering
- `backend/tests/test_backtester_api.py` — 40+ test cases: CRUD endpoints, validation, error handling

**Total: 245+ test cases across 6 modules**

Run with: `pytest backend/tests/ -v`

---

## Security Findings (Step 7b)

### Critical (5)
1. **CORS allows all origins** — `allow_origins=["*"]` in main.py. Fix: restrict to trusted domains.
2. **Hardcoded API key** — FDS_API_KEY has default value in config.py. Fix: require env variable.
3. **Unvalidated external data ingestion** — No ticker format validation. Fix: alphanumeric regex.
4. **Custom factor formula injection** — calculation_formula stored as raw string. Fix: whitelist allowed operations.
5. **Unrestricted backtest execution** — No rate limiting or resource quotas. Fix: max date range, concurrent limits.

### High (6 — key items)
6. Missing path parameter validation (gt=0 for IDs)
7. Generic exception handling leaking internal details
8. No authentication/authorization on any endpoint
9. Pagination parameters not validated (limit could be 1M)
10. SQL injection risk in search endpoint (wildcard chars)
11. Status strings not enum-validated

### Medium (7)
- Missing date validation (end < start), decimal range validation, weight sum validation
- No soft deletes or audit trail, unencrypted env storage, no HTTPS enforcement

### Low (7) / Info (3)
- No rate limiting on external APIs, print() instead of logging, no request ID tracking

**Total: 28 findings** (5 critical, 6 high, 7 medium, 7 low, 3 info)

---

## Performance Findings (Step 7c)

### Critical (3)
1. **N+1 factor score queries** — Per-ticker per-factor DB query in backtest loop. 500 securities × 5 factors × 60 rebalances = 150,000 queries. Fix: batch query.
2. **N+1 price queries in daily returns** — 2 queries per holding per day. Fix: batch price fetch.
3. **N+1 active universe loop** — Separate lifecycle query per security. Fix: single LEFT JOIN.

### High (5)
4. **Unbatched result inserts** — Individual INSERTs for 1,260+ daily results. Fix: bulk_insert_mappings.
5. **Missing/ineffective composite indexes** — Datetime conversion in WHERE prevents index usage. Fix: pre-compute thresholds.
6. **Memory explosion** — Full 60-month price history for 500 securities loaded at once (~126 MB). Fix: streaming/pagination.
7. **Unpaginated API results** — Full equity curve returned without pagination. Fix: paginate daily results.
8. **Frontend Recharts with 5000+ points** — UI freeze risk. Fix: aggregate to weekly/monthly.

### Medium (3)
9. Background task session management (connection pool exhaustion)
10. Data ingestion commits per-record (10x slower)
11. Placeholder FF regression implementation

**Total: 15 findings** (3 critical, 5 high, 3 medium, 4 low)

---

## Action Items (Must fix before delivery)

### Critical/High fixes needed:

**Performance (highest priority):**
- [ ] Batch factor score queries (eliminate N+1)
- [ ] Batch price queries in daily return calculation
- [ ] Rewrite active universe query as single JOIN
- [ ] Use bulk inserts for backtest results
- [ ] Implement actual FF5 regression (currently placeholder)

**Security:**
- [ ] Restrict CORS origins
- [ ] Remove hardcoded API key default
- [ ] Add input validation (ticker format, date ranges, pagination limits)
- [ ] Add path parameter validation (gt=0)
- [ ] Sanitize error messages (don't leak internals)

**Deferred (not blocking MVP):**
- Authentication/authorization (currently localhost-only)
- Rate limiting (single-user MVP)
- HTTPS (localhost dev)
- Frontend data aggregation (handle in v1.1)
