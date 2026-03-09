# AlphaDesk Testing Quick Start

## Installation

```bash
# Install test dependencies
pip install pytest sqlmodel fastapi

# Navigate to project root
cd /path/to/alpha-desk
```

## Run Tests

### All Tests
```bash
pytest backend/tests/ -v
```

### Specific Module
```bash
# Statistics tests
pytest backend/tests/test_statistics_calculator.py -v

# Engine tests
pytest backend/tests/test_backtest_engine.py -v

# Factor tests
pytest backend/tests/test_factor_calculator.py -v

# PiT tests
pytest backend/tests/test_pit_queries.py -v

# API tests
pytest backend/tests/test_backtester_api.py -v
```

### Specific Test Class
```bash
pytest backend/tests/test_statistics_calculator.py::TestSharpeRatio -v
```

### Specific Test
```bash
pytest backend/tests/test_statistics_calculator.py::TestSharpeRatio::test_sharpe_ratio_known_returns -v
```

## Coverage Reports

```bash
# Text report
pytest backend/tests/ --cov=backend --cov-report=term-missing

# HTML report
pytest backend/tests/ --cov=backend --cov-report=html
# Open htmlcov/index.html in browser
```

## Debug Mode

```bash
# Show print statements
pytest backend/tests/ -v -s

# Stop at first failure
pytest backend/tests/ -x

# Show local variables on failure
pytest backend/tests/ -l

# Use pdb on failure
pytest backend/tests/ --pdb
```

## Test Summary

| Module | Tests | Focus |
|--------|-------|-------|
| Statistics | 44 | Sharpe, Sortino, Calmar, Drawdown, Info Ratio, Hit Rate |
| Engine | 40+ | Rebalancing, Portfolio Construction, Turnover, PiT |
| Factors | 30+ | Ranking, Custom Factors, FF Exposures |
| PiT Queries | 50+ | Point-in-Time data correctness |
| API | 40+ | REST endpoints, validation, workflows |
| **Total** | **245+** | **Complete backtester coverage** |

## Database

All tests use **in-memory SQLite** (no PostgreSQL needed):
- Each test gets a fresh, isolated database
- Automatic cleanup after each test
- No external dependencies required
- Tests run fast (< 1 second per test)

## Key Features Tested

✓ All 8 performance metrics (Sharpe, Sortino, etc.)
✓ Rebalance frequencies (daily, weekly, monthly, quarterly, annual)
✓ Portfolio construction (top quintile selection)
✓ Turnover and transaction costs
✓ Point-in-Time data enforcement
✓ Factor scoring and ranking
✓ Custom factor calculations
✓ Fama-French exposures
✓ API CRUD operations
✓ Input validation and error handling
✓ Edge cases and extreme values

## Test Data

Each test uses realistic sample data:
- **Securities:** AAPL, MSFT, GOOGL, TSLA, AMZN
- **Dates:** 1 full year (252 trading days)
- **Prices:** Daily OHLCV data
- **Fundamentals:** Quarterly snapshots
- **Factors:** 3 custom factors
- **Backtest:** Monthly rebalancing, S&P 500 universe

## Common Commands

```bash
# List all tests
pytest backend/tests/ --collect-only

# Run tests matching pattern
pytest backend/tests/ -k "sharpe" -v

# Run with short summary
pytest backend/tests/ -q

# Parallel execution (requires pytest-xdist)
pytest backend/tests/ -n auto

# Stop after N failures
pytest backend/tests/ --maxfail=3

# Run last failed
pytest backend/tests/ --lf

# Run failed first
pytest backend/tests/ --ff
```

## File Locations

```
backend/tests/
├── conftest.py                 # Fixtures (8 fixtures)
├── test_statistics_calculator.py  # 44 tests
├── test_backtest_engine.py        # 40+ tests
├── test_factor_calculator.py      # 30+ tests
├── test_pit_queries.py            # 50+ tests
├── test_backtester_api.py         # 40+ tests
├── README.md                   # Detailed documentation
├── TEST_SUMMARY.md             # Feature coverage matrix
└── __init__.py                 # Package marker
```

## Next Steps

1. ✓ Install dependencies: `pip install pytest sqlmodel fastapi`
2. ✓ Run all tests: `pytest backend/tests/ -v`
3. ✓ Generate coverage: `pytest backend/tests/ --cov=backend`
4. ✓ Check specific modules: `pytest backend/tests/test_statistics_calculator.py -v`
5. ✓ Integrate with CI/CD (GitHub Actions, etc.)

## Troubleshooting

**Error: ModuleNotFoundError: No module named 'backend'**
- Run pytest from project root: `cd /path/to/alpha-desk`
- Or: `pytest backend/tests/` from root

**Error: "No such table"**
- Ensure conftest.py is in backend/tests/
- Check that all imports are correct

**Tests running slowly**
- Use: `pytest backend/tests/ -q` for quick runs
- Skip coverage for faster iteration: `pytest backend/tests/ --no-cov`

**Need more details?**
- See `backend/tests/README.md` for comprehensive documentation
- See `backend/tests/TEST_SUMMARY.md` for feature coverage matrix

---

**Ready to test?** Run: `pytest backend/tests/ -v`
