"""
Shared test fixtures and configuration for AlphaDesk tests.
Uses in-memory SQLite database for fast testing without external dependencies.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.securities import Security, SecurityStatus, SecurityLifecycleEvent
from backend.models.market_data import PriceHistory, FundamentalsSnapshot
from backend.models.factors import FactorDefinition, CustomFactorScore
from backend.models.backtests import (
    Backtest,
    BacktestConfiguration,
    BacktestFactorAllocation,
    BacktestResult,
    BacktestStatistic,
)
from backend.models.events import (
    Event,
    EventClassificationRule,
    AlphaDecayWindow,
    EventAlertConfiguration,
)
from backend.models.earnings import (
    EarningsEstimate,
    EarningsActual,
    SmartEstimateWeights,
    AnalystScorecard,
    PEADMeasurement,
    EarningsSignal,
)


@pytest.fixture(name="session")
def session_fixture():
    """
    Create an in-memory SQLite database session for testing.
    Automatically creates all tables and rolls back after each test.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Create session
    session = Session(engine)

    yield session

    # Cleanup
    session.close()


@pytest.fixture(name="test_client")
def test_client_fixture(session):
    """
    Create a FastAPI test client with test database session.
    """

    def get_session_override():
        return session

    app.dependency_overrides[
        "backend.database.get_session"
    ] = get_session_override

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(name="sample_securities")
def sample_securities_fixture(session: Session):
    """
    Create sample securities for testing.
    Returns list of Security objects (Apple, Microsoft, Google, Tesla, Amazon).
    """
    securities = [
        Security(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            industry="Semiconductors",
            current_status=SecurityStatus.ACTIVE,
        ),
        Security(
            ticker="MSFT",
            name="Microsoft Corporation",
            sector="Information Technology",
            industry="Software",
            current_status=SecurityStatus.ACTIVE,
        ),
        Security(
            ticker="GOOGL",
            name="Alphabet Inc.",
            sector="Communication Services",
            industry="Internet",
            current_status=SecurityStatus.ACTIVE,
        ),
        Security(
            ticker="TSLA",
            name="Tesla Inc.",
            sector="Consumer Discretionary",
            industry="Automobiles",
            current_status=SecurityStatus.ACTIVE,
        ),
        Security(
            ticker="AMZN",
            name="Amazon.com Inc.",
            sector="Consumer Discretionary",
            industry="Internet Retail",
            current_status=SecurityStatus.ACTIVE,
        ),
    ]

    for sec in securities:
        session.add(sec)

    session.commit()

    return securities


@pytest.fixture(name="sample_prices")
def sample_prices_fixture(session: Session, sample_securities):
    """
    Create sample price history data for testing.
    Creates 252 trading days (1 year) of daily prices for each security.
    """
    prices = []
    base_date = date(2023, 1, 1)
    tickers = [sec.ticker for sec in sample_securities]

    # Generate prices for 252 trading days
    for day_offset in range(252):
        current_date = base_date + timedelta(days=day_offset)

        # Skip weekends (simple approximation - just skip Saturdays and Sundays)
        if current_date.weekday() >= 5:
            continue

        for ticker_idx, ticker in enumerate(tickers):
            # Generate realistic price progression with small random walk
            base_price = [150.0, 300.0, 2800.0, 200.0, 3300.0][ticker_idx]
            # Add some noise to prices
            daily_return = 0.0005 * (ticker_idx + 1)  # Different returns per stock
            price = base_price * (1 + daily_return) ** day_offset

            price_record = PriceHistory(
                ticker=ticker,
                date=current_date,
                open=Decimal(str(price * 0.99)),
                high=Decimal(str(price * 1.02)),
                low=Decimal(str(price * 0.98)),
                close=Decimal(str(price)),
                adjusted_close=Decimal(str(price)),
                volume=1000000,
                ingestion_timestamp=datetime.combine(
                    current_date, datetime.max.time(), tzinfo=timezone.utc
                ),
            )
            prices.append(price_record)
            session.add(price_record)

    session.commit()

    return prices


@pytest.fixture(name="sample_fundamentals")
def sample_fundamentals_fixture(session: Session, sample_securities):
    """
    Create sample fundamental data for testing.
    Creates quarterly fundamental snapshots for each security.
    """
    fundamentals = []
    base_date = date(2023, 1, 1)
    tickers = [sec.ticker for sec in sample_securities]

    # Create fundamentals for 4 quarters
    for quarter_offset in range(4):
        quarter_date = base_date + timedelta(days=quarter_offset * 90)

        for ticker_idx, ticker in enumerate(tickers):
            # Sample metrics
            metrics = [
                ("free_cash_flow", Decimal(str(10000000000 * (ticker_idx + 1)))),
                ("market_cap", Decimal(str(2000000000000 * (ticker_idx + 1)))),
                ("net_income", Decimal(str(5000000000 * (ticker_idx + 1)))),
                ("total_debt", Decimal(str(1000000000 * (ticker_idx + 1)))),
                ("stockholders_equity", Decimal(str(1500000000000 * (ticker_idx + 1)))),
            ]

            for metric_name, metric_value in metrics:
                fundamental = FundamentalsSnapshot(
                    ticker=ticker,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    source_document_date=quarter_date,
                    fiscal_period_end=quarter_date,
                    ingestion_timestamp=datetime.combine(
                        quarter_date, datetime.max.time(), tzinfo=timezone.utc
                    ),
                )
                fundamentals.append(fundamental)
                session.add(fundamental)

    session.commit()

    return fundamentals


@pytest.fixture(name="sample_factors")
def sample_factors_fixture(session: Session):
    """
    Create sample factor definitions for testing.
    """
    factors = [
        FactorDefinition(
            name="FCF Yield",
            description="Free Cash Flow Yield",
            factor_type="custom",
            calculation_formula="free_cash_flow / market_cap",
            source="custom",
            created_by="test_user",
        ),
        FactorDefinition(
            name="Earnings Yield",
            description="Earnings Yield (E/P)",
            factor_type="custom",
            calculation_formula="net_income / market_cap",
            source="custom",
            created_by="test_user",
        ),
        FactorDefinition(
            name="Leverage",
            description="Debt to Equity Ratio",
            factor_type="custom",
            calculation_formula="total_debt / stockholders_equity",
            source="custom",
            created_by="test_user",
        ),
    ]

    for factor in factors:
        session.add(factor)

    session.commit()

    return factors


@pytest.fixture(name="sample_backtest")
def sample_backtest_fixture(session: Session, sample_factors):
    """
    Create a sample backtest configuration for testing.
    """
    backtest = Backtest(
        name="Test Backtest",
        backtest_type="factor_combination",
        status="DRAFT",
    )
    session.add(backtest)
    session.flush()  # Get the ID without committing

    # Create configuration
    config = BacktestConfiguration(
        backtest_id=backtest.id,
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        rebalance_frequency="monthly",
        universe_selection="sp500",
        commission_bps=Decimal("5.0"),
        slippage_bps=Decimal("2.0"),
        benchmark_ticker="SPY",
        rolling_window_months=60,
    )
    session.add(config)

    # Add factor allocations
    allocations = [
        BacktestFactorAllocation(
            backtest_id=backtest.id,
            factor_id=sample_factors[0].id,
            weight=Decimal("0.5"),
        ),
        BacktestFactorAllocation(
            backtest_id=backtest.id,
            factor_id=sample_factors[1].id,
            weight=Decimal("0.5"),
        ),
    ]

    for allocation in allocations:
        session.add(allocation)

    session.commit()

    return backtest


@pytest.fixture(name="sample_backtest_results")
def sample_backtest_results_fixture(session: Session, sample_backtest):
    """
    Create sample backtest results for testing statistics.
    """
    results = []
    base_date = date(2023, 1, 1)

    # Create daily results for 252 trading days
    portfolio_value = Decimal("1000000")

    for day_offset in range(252):
        current_date = base_date + timedelta(days=day_offset)

        # Skip weekends
        if current_date.weekday() >= 5:
            continue

        # Generate a realistic daily return (mean ~0.05%, std ~1%)
        daily_return = Decimal(str(0.0005 + 0.01 * (day_offset % 10) / 100))
        portfolio_value = portfolio_value * (1 + daily_return)

        result = BacktestResult(
            backtest_id=sample_backtest.id,
            date=current_date,
            portfolio_value=portfolio_value,
            daily_return=daily_return,
            benchmark_return=Decimal(str(0.0003 + 0.005 * (day_offset % 10) / 100)),
            turnover=Decimal("0.1") if day_offset % 21 == 0 else Decimal("0.0"),
            holdings_count=20,
        )
        results.append(result)
        session.add(result)

    session.commit()

    return results


@pytest.fixture(name="sample_security_lifecycle")
def sample_security_lifecycle_fixture(session: Session, sample_securities):
    """
    Create security lifecycle events for testing PiT queries.
    """
    events = []

    # Add activation events for all securities
    for sec in sample_securities:
        event = SecurityLifecycleEvent(
            ticker=sec.ticker,
            event_type="IPO",
            event_date=date(2015, 1, 1),
            details={"reason": "Initial Public Offering"},
        )
        events.append(event)
        session.add(event)

    session.commit()

    return events


@pytest.fixture(name="sample_events")
def sample_events_fixture(session: Session, sample_securities):
    """
    Create sample events for testing Event Scanner functionality.
    """
    events = []
    base_date = date(2023, 1, 1)
    now = datetime.now(timezone.utc)

    # Create various event types
    event_configs = [
        ("AAPL", "earnings_announcement", 3, "Q1 Earnings"),
        ("AAPL", "insider_trade_buy_large", 4, "CEO purchase"),
        ("MSFT", "sec_filing_10k", 2, "Annual Report"),
        ("GOOGL", "beneficial_ownership_13d", 4, "Activist stake"),
        ("TSLA", "sec_filing_8k_item_1_01", 5, "Bankruptcy filing"),
        ("AMZN", "dividend_ex_date", 1, "Dividend"),
    ]

    for ticker, event_type, severity, headline in event_configs:
        event = Event(
            ticker=ticker,
            event_type=event_type,
            severity_score=severity,
            detected_at=now - timedelta(days=len(events)),
            event_date=base_date + timedelta(days=len(events)),
            source="SEC_EDGAR" if "sec_filing" in event_type else "YFINANCE",
            headline=headline,
            description=f"{headline} for {ticker}",
            metadata={
                "source_type": "SEC_EDGAR" if "sec_filing" in event_type else "YFINANCE",
            },
        )
        events.append(event)
        session.add(event)

    session.commit()

    return events


@pytest.fixture(name="sample_classification_rules")
def sample_classification_rules_fixture(session: Session):
    """
    Create sample event classification rules for testing.
    """
    rules = [
        EventClassificationRule(
            classification="earnings_announcement",
            pattern_type="calendar_event",
            pattern_value={"event_type": "earnings"},
            confidence_score=95,
            enabled=True,
            description="Earnings announcement detection",
        ),
        EventClassificationRule(
            classification="insider_trade_buy",
            pattern_type="filing_form",
            pattern_value={"filing_type": "4", "transaction_type": "buy"},
            confidence_score=90,
            enabled=True,
            description="Insider buy transaction",
        ),
        EventClassificationRule(
            classification="bankruptcy",
            pattern_type="filing_form",
            pattern_value={"filing_type": "8-K", "item_number": "1.01"},
            confidence_score=99,
            enabled=True,
            description="Bankruptcy filing (8-K Item 1.01)",
        ),
    ]

    for rule in rules:
        session.add(rule)

    session.commit()

    return rules


@pytest.fixture(name="sample_alpha_decay_windows")
def sample_alpha_decay_windows_fixture(session: Session, sample_events):
    """
    Create sample alpha decay windows for testing.
    """
    windows = []

    for event in sample_events[:3]:  # Create windows for first 3 events
        for window_type, days in [("1d", 1), ("5d", 5), ("21d", 21)]:
            window = AlphaDecayWindow(
                event_id=event.event_id,
                window_type=window_type,
                abnormal_return=Decimal(str(0.001 * days)),  # Vary by window
                benchmark_return=Decimal("0.0005"),
                measured_at=datetime.now(timezone.utc),
                confidence=Decimal("0.95"),
                sample_size=1,
            )
            windows.append(window)
            session.add(window)

    session.commit()

    return windows


@pytest.fixture(name="sample_alert_configuration")
def sample_alert_configuration_fixture(session: Session):
    """
    Create sample alert configuration for testing.
    """
    config = EventAlertConfiguration(
        event_type_filter=["earnings_announcement", "insider_trade_buy_large", "sec_filing_8k_item_1_01"],
        severity_threshold=2,
        enabled=True,
        tickers_filter=["AAPL", "MSFT", "GOOGL"],
    )
    session.add(config)
    session.commit()

    return config


# ==================== Earnings-Related Fixtures ====================


@pytest.fixture(name="sample_earnings_estimates")
def sample_earnings_estimates_fixture(session: Session):
    """
    Create sample earnings estimates for testing.
    """
    now = datetime.now(timezone.utc)
    estimates = []

    # Create consensus and individual estimates for multiple tickers and quarters
    tickers = ["AAPL", "MSFT", "GOOGL"]
    for ticker in tickers:
        for quarter in ["2024Q1", "2024Q2"]:
            # Consensus estimate
            consensus = EarningsEstimate(
                ticker=ticker,
                fiscal_quarter=quarter,
                estimate_type="consensus",
                eps_estimate=Decimal(str(5.0 + hash(ticker) % 3)),
                estimate_date=now - timedelta(days=20),
                analyst_broker=None,
            )
            estimates.append(consensus)
            session.add(consensus)

            # Individual estimates
            for i in range(3):
                individual = EarningsEstimate(
                    ticker=ticker,
                    fiscal_quarter=quarter,
                    estimate_type="individual",
                    eps_estimate=Decimal(str(5.0 + hash(ticker + str(i)) % 5 * 0.1)),
                    estimate_date=now - timedelta(days=20 - i * 5),
                    analyst_broker=f"Analyst_{i}",
                )
                estimates.append(individual)
                session.add(individual)

    session.commit()
    return estimates


@pytest.fixture(name="sample_earnings_actuals")
def sample_earnings_actuals_fixture(session: Session):
    """
    Create sample actual earnings for testing.
    """
    actuals = []

    tickers = ["AAPL", "MSFT", "GOOGL"]
    for ticker in tickers:
        for quarter_idx, quarter in enumerate(["2024Q1", "2024Q2"]):
            actual = EarningsActual(
                ticker=ticker,
                fiscal_quarter=quarter,
                actual_eps=Decimal(str(5.0 + hash(ticker) % 3 + 0.1 * quarter_idx)),
                report_date=date(2024, 1, 15) + timedelta(days=90 * quarter_idx),
                report_time="post_market",
                surprise_vs_consensus=Decimal(str(1.5 + quarter_idx * 0.5)),
                source="yfinance",
            )
            actuals.append(actual)
            session.add(actual)

    session.commit()
    return actuals


@pytest.fixture(name="sample_smart_estimate_weights")
def sample_smart_estimate_weights_fixture(session: Session):
    """
    Create sample SmartEstimate weight configurations.
    """
    weights = [
        SmartEstimateWeights(
            weight_type="recency_decay",
            parameter_name="half_life_days",
            parameter_value=Decimal("30"),
            description="30-day half-life for recency decay",
        ),
        SmartEstimateWeights(
            weight_type="accuracy_tier",
            parameter_name="tier_a_weight",
            parameter_value=Decimal("1.5"),
            description="Tier A analyst weight (top quartile)",
        ),
        SmartEstimateWeights(
            weight_type="accuracy_tier",
            parameter_name="tier_b_weight",
            parameter_value=Decimal("1.0"),
            description="Tier B analyst weight (mid tier)",
        ),
        SmartEstimateWeights(
            weight_type="accuracy_tier",
            parameter_name="tier_c_weight",
            parameter_value=Decimal("0.5"),
            description="Tier C analyst weight (bottom quartile)",
        ),
    ]

    for w in weights:
        session.add(w)

    session.commit()
    return weights


@pytest.fixture(name="sample_analyst_scorecards")
def sample_analyst_scorecards_fixture(session: Session):
    """
    Create sample analyst accuracy scorecards.
    """
    scorecards = [
        AnalystScorecard(
            analyst_broker="Goldman Sachs",
            ticker="AAPL",
            total_estimates=100,
            accurate_count=95,
            directional_accuracy=Decimal("92.0"),
            avg_error_pct=Decimal("2.5"),
            period_start=date(2023, 1, 1),
            period_end=date(2024, 1, 1),
        ),
        AnalystScorecard(
            analyst_broker="JP Morgan",
            ticker="MSFT",
            total_estimates=80,
            accurate_count=65,
            directional_accuracy=Decimal("85.0"),
            avg_error_pct=Decimal("4.2"),
            period_start=date(2023, 1, 1),
            period_end=date(2024, 1, 1),
        ),
        AnalystScorecard(
            analyst_broker="Morgan Stanley",
            ticker="GOOGL",
            total_estimates=60,
            accurate_count=30,
            directional_accuracy=Decimal("70.0"),
            avg_error_pct=Decimal("8.5"),
            period_start=date(2023, 1, 1),
            period_end=date(2024, 1, 1),
        ),
    ]

    for scorecard in scorecards:
        session.add(scorecard)

    session.commit()
    return scorecards


@pytest.fixture(name="sample_pead_measurements")
def sample_pead_measurements_fixture(session: Session):
    """
    Create sample PEAD measurements for testing.
    """
    measurements = []

    tickers = ["AAPL", "MSFT", "GOOGL"]
    for ticker_idx, ticker in enumerate(tickers):
        for quarter_idx, quarter in enumerate(["2024Q1", "2024Q2"]):
            direction = "positive" if ticker_idx % 2 == 0 else "negative"
            pead = PEADMeasurement(
                ticker=ticker,
                fiscal_quarter=quarter,
                earnings_date=date(2024, 1, 15) + timedelta(days=90 * quarter_idx),
                surprise_direction=direction,
                surprise_magnitude=Decimal(str(2.0 + ticker_idx * 0.5)),
                car_1d=Decimal(str(0.5 + ticker_idx * 0.1)),
                car_5d=Decimal(str(1.0 + ticker_idx * 0.2)),
                car_21d=Decimal(str(2.0 + ticker_idx * 0.3)),
                car_60d=Decimal(str(3.5 + ticker_idx * 0.5)),
                benchmark_ticker="SPY",
                measured_at=datetime.now(timezone.utc),
            )
            measurements.append(pead)
            session.add(pead)

    session.commit()
    return measurements


@pytest.fixture(name="sample_earnings_signals")
def sample_earnings_signals_fixture(session: Session):
    """
    Create sample earnings signals for testing.
    """
    signals = []
    now = datetime.now(timezone.utc)

    tickers = ["AAPL", "MSFT", "GOOGL"]
    for ticker_idx, ticker in enumerate(tickers):
        for quarter_idx, quarter in enumerate(["2024Q1", "2024Q2"]):
            signal_type = "buy" if ticker_idx % 2 == 0 else "sell"
            signal = EarningsSignal(
                ticker=ticker,
                fiscal_quarter=quarter,
                signal_date=now - timedelta(days=5),
                signal_type=signal_type,
                confidence=70 + ticker_idx * 5,
                smart_estimate_eps=Decimal(str(5.0 + ticker_idx * 0.1)),
                consensus_eps=Decimal(str(5.0 + ticker_idx * 0.05)),
                divergence_pct=Decimal(str(2.0 + quarter_idx * 0.5)),
                days_to_earnings=5 - quarter_idx,
                valid_until=now + timedelta(days=5),
            )
            signals.append(signal)
            session.add(signal)

    session.commit()
    return signals
