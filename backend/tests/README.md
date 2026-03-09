# AlphaDesk Factor Backtester Test Suite

Comprehensive test suite for the AlphaDesk Factor Backtester feature. All tests use an in-memory SQLite database for fast, isolated test execution without external dependencies.

## Test Files Overview

### 1. `conftest.py` - Shared Fixtures and Configuration

**Purpose:** Provides fixtures for all tests.

**Fixtures:**
- `session` - In-memory SQLite database session
- `test_client` - FastAPI TestClient for API testing
- `sample_securities` - 5 test securities (AAPL, MSFT, GOOGL, TSLA, AMZN)
- `sample_prices` - 252 days of daily price data for each security
- `sample_fundamentals` - Quarterly fundamental snapshots (FCF, market cap, earnings, debt, equity)
- `sample_factors` - 3 factor definitions (FCF Yield, Earnings Yield, Leverage)
- `sample_backtest` - Configured backtest with factor allocations
- `sample_backtest_results` - 252 daily backtest results
- `sample_security_lifecycle` - Security lifecycle events for PiT testing

**Key Features:**
- Uses SQLite in-memory database (`:memory:`) for speed
- Automatic table creation and cleanup
- Realistic sample data with proper relationships
- Data spans 252 trading days (1 full year)

### 2. `test_statistics_calculator.py` - Performance Metrics

**Purpose:** Unit tests for all statistical calculations.

**Test Classes:**
- `TestSharpeRatio` - Sharpe ratio with multiple risk-free rates
- `TestSortinoRatio` - Downside volatility penalty metrics
- `TestMaxDrawdown` - Peak-to-trough loss calculations
- `TestCalmarRatio` - Return to drawdown ratio
- `TestInformationRatio` - Excess return metrics
- `TestHitRate` - Percentage of positive returns
- `TestAnnualizedReturn` - Compound annual returns
- `TestAnnualizedVolatility` - Annualized standard deviation
- `TestCalculateAll` - All metrics computed together
- `TestEdgeCases` - NaN, extreme values, large datasets

**Coverage:**
- 45+ test cases
- Known-input validation
- Edge cases (empty, single value, zero volatility)
- Consistency checks between metrics

### 3. `test_backtest_engine.py` - Portfolio Construction

**Purpose:** Integration tests for backtest walk-forward engine.

**Test Classes:**
- `TestGenerateRebalanceDates` - Monthly, quarterly, annual, weekly, daily frequencies
- `TestConstructPortfolio` - Quintile selection, equal-weight construction
- `TestCalculateTurnover` - Portfolio changes and transaction costs
- `TestPitEnforcement` - Point-in-Time data correctness
- `TestGetAllTradingDates` - Date extraction from price data
- `TestComputeFactorScores` - Composite factor score weighting
- `TestCalculateDailyReturns` - Portfolio return calculations
- `TestGetBenchmarkReturn` - Benchmark comparison returns

**Coverage:**
- 40+ test cases
- Rebalance frequency validation
- Portfolio construction logic
- Turnover and cost calculations
- PiT enforcement verification

### 4. `test_factor_calculator.py` - Factor Scoring

**Purpose:** Unit tests for factor calculation and ranking.

**Test Classes:**
- `TestRankUniverse` - Percentile ranking across securities
- `TestCustomFactorCalculation` - FCF yield, P/E ratio, D/E ratio
- `TestCalculateCustomFactor` - Formula-based factor computation
- `TestCalculateFamaFrenchExposures` - FF factor betas
- `TestFactorCalculatorEdgeCases` - Single ticker, large universe

**Coverage:**
- 30+ test cases
- Percentile ranking validation
- Custom factor formulas
- FF5 factor exposure calculation
- Edge case handling

### 5. `test_pit_queries.py` - Point-in-Time Data

**Purpose:** Ensures backtests use only historically available data.

**Test Classes:**
- `TestGetPricesPIT` - Price history as of specific date
- `TestGetFundamentalsPIT` - Fundamental data temporal constraints
- `TestGetActiveUniversePIT` - Active securities excluding delisted/acquired
- `TestPITConsistency` - Cross-query consistency
- `TestPITEdgeCases` - End-of-day, future dates, far past

**Coverage:**
- 50+ test cases
- Ingestion timestamp enforcement
- Source document date validation
- Delisting/acquisition/bankruptcy exclusion
- Walk-forward progression validation

### 6. `test_backtester_api.py` - REST Endpoints

**Purpose:** FastAPI endpoint tests using TestClient.

**Test Classes:**
- `TestCreateBacktest` - POST /api/backtests with validation
- `TestGetBacktest` - GET /api/backtests/{id}
- `TestListBacktests` - GET /api/backtests with pagination
- `TestGetBacktestStatus` - Status endpoint
- `TestGetBacktestResults` - Daily results retrieval
- `TestGetBacktestStatistics` - Performance metrics
- `TestUpdateBacktest` - PUT endpoint
- `TestDeleteBacktest` - DELETE endpoint
- `TestFactorAllocationAPI` - Factor management
- `TestAPIValidation` - Input validation
- `TestAPIIntegration` - Full workflows

**Coverage:**
- 40+ test cases
- CRUD operations (Create, Read, Update, Delete)
- Validation and error handling
- Pagination and filtering
- End-to-end workflows

## Running the Tests

### Prerequisites

```bash
# Install dependencies
pip install pytest pytest-cov sqlmodel fastapi
```

### Run All Tests

```bash
pytest backend/tests/
```

### Run Specific Test File

```bash
pytest backend/tests/test_statistics_calculator.py -v
```

### Run Specific Test Class

```bash
pytest backend/tests/test_statistics_calculator.py::TestSharpeRatio -v
```

### Run Specific Test

```bash
pytest backend/tests/test_statistics_calculator.py::TestSharpeRatio::test_sharpe_ratio_known_returns -v
```

### Run with Coverage Report

```bash
pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term-missing
```

### Run by Test Category

```bash
# Unit tests only
pytest backend/tests/ -m "not integration"

# API tests only
pytest backend/tests/ -m api

# PiT tests only
pytest backend/tests/ -m pit
```

### Run with Verbose Output

```bash
pytest backend/tests/ -vv  # Extra verbose
pytest backend/tests/ -v   # Verbose
```

## Test Statistics

| Module | Test Classes | Test Cases | Coverage Focus |
|--------|-------------|-----------|-----------------|
| `conftest.py` | - | - | Fixtures & Setup |
| `test_statistics_calculator.py` | 10 | 45+ | All performance metrics |
| `test_backtest_engine.py` | 7 | 40+ | Engine logic & PiT |
| `test_factor_calculator.py` | 5 | 30+ | Factor computation |
| `test_pit_queries.py` | 5 | 50+ | PiT correctness |
| `test_backtester_api.py` | 11 | 40+ | API endpoints |
| **Total** | **38** | **245+** | **All features** |

## Key Test Patterns

### 1. Unit Tests with Known Inputs

```python
def test_sharpe_ratio_known_returns(self):
    returns = [0.01, -0.005, 0.008, 0.002, -0.003]
    sharpe = StatisticsCalculator.sharpe_ratio(returns)
    assert isinstance(sharpe, float)
    assert sharpe > 0
```

### 2. Edge Case Testing

```python
def test_sharpe_ratio_empty_returns(self):
    returns = []
    sharpe = StatisticsCalculator.sharpe_ratio(returns)
    assert sharpe == 0.0
```

### 3. Integration Testing with Fixtures

```python
def test_rank_universe_basic(self, session: Session, sample_securities, sample_factors):
    calculator = FactorCalculator(session)
    tickers = [sec.ticker for sec in sample_securities]
    ranks = calculator.rank_universe(factor_id, tickers, as_of)
    assert isinstance(ranks, dict)
```

### 4. API Testing with TestClient

```python
def test_create_backtest_valid_input(self, test_client: TestClient, sample_factors):
    request_data = {...}
    response = test_client.post("/api/backtests", json=request_data)
    assert response.status_code == 200
```

## Fixture Dependencies

```
conftest.py
├── session (in-memory SQLite)
│   ├── sample_securities (5 stocks)
│   ├── sample_prices (252 days × 5 stocks)
│   ├── sample_fundamentals (4 quarters × 5 stocks)
│   ├── sample_factors (3 factors)
│   ├── sample_backtest (with allocations)
│   ├── sample_backtest_results (252 daily results)
│   └── sample_security_lifecycle (events)
└── test_client (with session override)
```

## Database Setup in Tests

All tests use an in-memory SQLite database to:
1. **Eliminate external dependencies** - No PostgreSQL required
2. **Ensure isolation** - Each test gets a clean database
3. **Improve speed** - In-memory operations are fast
4. **Simplify CI/CD** - No database setup needed

```python
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

## Important Notes

### PiT (Point-in-Time) Testing

The test suite extensively validates that:
- Price queries exclude future data
- Fundamental queries respect source document dates
- Active universe excludes delisted/acquired securities
- Backtest walk-forward respects historical data availability

### Sample Data

All fixtures use realistic data:
- **Prices:** 1 year of daily data (252 trading days)
- **Fundamentals:** 4 quarterly snapshots
- **Returns:** Positive drift with realistic volatility
- **Securities:** Real ticker symbols with correct sectors

### Test Isolation

Each test:
1. Gets a fresh, empty in-memory database
2. Has fixtures automatically set up
3. Cleans up after completion
4. Doesn't affect other tests

## Extending the Test Suite

### Adding a New Test Class

```python
class TestNewFeature:
    """Test description."""

    def test_basic_functionality(self, session: Session, sample_backtest):
        """Test that feature works."""
        # Arrange
        calculator = FactorCalculator(session)

        # Act
        result = calculator.some_method()

        # Assert
        assert result is not None
```

### Adding a New Fixture

```python
@pytest.fixture(name="new_fixture")
def new_fixture_fixture(session: Session):
    """Create test data for new feature."""
    # Setup
    data = SomeModel(...)
    session.add(data)
    session.commit()

    # Return
    yield data

    # Cleanup (automatic with session scope)
```

## Debugging Tests

### Print Debug Output

```bash
pytest backend/tests/test_file.py -v -s
```

The `-s` flag prevents output capture and shows print statements.

### Use pdb Breakpoints

```python
def test_something(self):
    result = some_function()
    import pdb; pdb.set_trace()  # Debugger will pause here
    assert result == expected
```

### Run Single Test

```bash
pytest backend/tests/test_file.py::TestClass::test_method -vv
```

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'backend'`

**Solution:** Run pytest from project root directory:
```bash
cd /path/to/alpha-desk
pytest backend/tests/
```

### Issue: Tests fail with `"No such table" error`

**Solution:** Ensure conftest.py creates tables:
```python
SQLModel.metadata.create_all(engine)
```

### Issue: Fixtures not found

**Solution:** Ensure `conftest.py` is in `backend/tests/` directory

## Next Steps

1. **Run full test suite** to verify everything works
2. **Add markers** to categorize tests for CI/CD
3. **Set up coverage thresholds** in CI/CD pipeline
4. **Integrate with GitHub Actions** or similar
5. **Monitor test execution time** and optimize slow tests

## Test Coverage Goals

- **Statements:** > 85%
- **Branches:** > 80%
- **Functions:** > 90%
- **Lines:** > 85%

Run `pytest --cov=backend --cov-report=html` to generate coverage report.

## References

- [pytest Documentation](https://docs.pytest.org/)
- [SQLModel Testing](https://sqlmodel.tiangolo.com/tutorial/testing/)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-databases/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
