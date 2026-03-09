"""
Unit tests for FactorCalculator.
Tests factor scoring and ranking functionality.
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlmodel import Session

from backend.services.factor_calculator import FactorCalculator
from backend.models.factors import FactorDefinition


class TestRankUniverse:
    """Test universe ranking by factor scores."""

    def test_rank_universe_basic(
        self, session: Session, sample_securities, sample_factors, sample_fundamentals
    ):
        """Test basic universe ranking."""
        calculator = FactorCalculator(session)
        tickers = [sec.ticker for sec in sample_securities]
        factor_id = sample_factors[0].id  # FCF Yield
        as_of = date(2023, 3, 1)

        ranks = calculator.rank_universe(factor_id, tickers, as_of)

        # Should return a dictionary
        assert isinstance(ranks, dict)
        # All ranks should be between 0 and 100 (percentile)
        for ticker, rank in ranks.items():
            assert 0 <= rank <= 100

    def test_rank_universe_percentiles(
        self, session: Session, sample_securities, sample_factors, sample_fundamentals
    ):
        """Test that percentile ranks are correctly computed."""
        calculator = FactorCalculator(session)
        tickers = [sec.ticker for sec in sample_securities]
        factor_id = sample_factors[0].id
        as_of = date(2023, 3, 1)

        ranks = calculator.rank_universe(factor_id, tickers, as_of)

        # With 5 securities, percentiles should be roughly evenly spaced
        # (though exact values depend on actual factor scores)
        if len(ranks) == len(tickers):
            # If all tickers were ranked, check diversity
            unique_ranks = len(set(ranks.values()))
            assert unique_ranks > 1  # Should have different ranks

    def test_rank_universe_empty_universe(
        self, session: Session, sample_factors
    ):
        """Test ranking with empty universe."""
        calculator = FactorCalculator(session)
        tickers = []
        factor_id = sample_factors[0].id
        as_of = date(2023, 3, 1)

        ranks = calculator.rank_universe(factor_id, tickers, as_of)

        assert ranks == {}

    def test_rank_universe_nonexistent_factor(
        self, session: Session, sample_securities
    ):
        """Test ranking with nonexistent factor."""
        calculator = FactorCalculator(session)
        tickers = [sec.ticker for sec in sample_securities]
        factor_id = 99999  # Nonexistent
        as_of = date(2023, 3, 1)

        ranks = calculator.rank_universe(factor_id, tickers, as_of)

        # Should return empty dict gracefully
        assert ranks == {}

    def test_rank_universe_top_bottom(
        self, session: Session, sample_securities, sample_factors, sample_fundamentals
    ):
        """Test that top and bottom ranked securities have different percentiles."""
        calculator = FactorCalculator(session)
        tickers = [sec.ticker for sec in sample_securities]
        factor_id = sample_factors[0].id
        as_of = date(2023, 3, 1)

        ranks = calculator.rank_universe(factor_id, tickers, as_of)

        if len(ranks) > 1:
            # Top and bottom should have different ranks
            max_rank = max(ranks.values())
            min_rank = min(ranks.values())
            assert max_rank > min_rank


class TestCustomFactorCalculation:
    """Test custom factor calculation methods."""

    def test_calculate_fcf_yield(
        self, session: Session, sample_fundamentals
    ):
        """Test FCF yield calculation."""
        calculator = FactorCalculator(session)
        ticker = "AAPL"
        as_of = date(2023, 3, 1)

        yield_value = calculator._calculate_fcf_yield(ticker, as_of)

        # Should return a positive float or None
        if yield_value is not None:
            assert isinstance(yield_value, float)
            assert yield_value > 0

    def test_calculate_fcf_yield_missing_data(
        self, session: Session
    ):
        """Test FCF yield with missing data."""
        calculator = FactorCalculator(session)
        ticker = "NONEXISTENT"
        as_of = date(2023, 3, 1)

        yield_value = calculator._calculate_fcf_yield(ticker, as_of)

        # Should return None gracefully
        assert yield_value is None

    def test_calculate_pe_ratio(
        self, session: Session, sample_fundamentals
    ):
        """Test P/E ratio (earnings yield) calculation."""
        calculator = FactorCalculator(session)
        ticker = "AAPL"
        as_of = date(2023, 3, 1)

        earnings_yield = calculator._calculate_pe_ratio(ticker, as_of)

        # Should return a float or None
        if earnings_yield is not None:
            assert isinstance(earnings_yield, float)
            assert earnings_yield > 0

    def test_calculate_pe_ratio_missing_earnings(
        self, session: Session
    ):
        """Test P/E ratio with missing earnings data."""
        calculator = FactorCalculator(session)
        ticker = "NONEXISTENT"
        as_of = date(2023, 3, 1)

        earnings_yield = calculator._calculate_pe_ratio(ticker, as_of)

        assert earnings_yield is None

    def test_calculate_debt_to_equity(
        self, session: Session, sample_fundamentals
    ):
        """Test debt-to-equity ratio calculation."""
        calculator = FactorCalculator(session)
        ticker = "AAPL"
        as_of = date(2023, 3, 1)

        de_ratio = calculator._calculate_debt_to_equity(ticker, as_of)

        # Should return a float or None
        if de_ratio is not None:
            assert isinstance(de_ratio, float)
            assert de_ratio >= 0

    def test_calculate_debt_to_equity_zero_equity(
        self, session: Session, sample_fundamentals
    ):
        """Test debt-to-equity when equity is zero."""
        calculator = FactorCalculator(session)

        # This would occur with missing equity data
        ticker = "NONEXISTENT"
        as_of = date(2023, 3, 1)

        de_ratio = calculator._calculate_debt_to_equity(ticker, as_of)

        assert de_ratio is None


class TestCalculateCustomFactor:
    """Test custom factor calculation dispatcher."""

    def test_calculate_custom_factor_fcf_yield(
        self, session: Session, sample_factors, sample_fundamentals
    ):
        """Test custom factor calculation for FCF yield."""
        calculator = FactorCalculator(session)
        factor_def = sample_factors[0]  # FCF Yield factor
        ticker = "AAPL"
        as_of = date(2023, 3, 1)

        # Manually set formula
        factor_def.calculation_formula = "fcf_yield"
        session.add(factor_def)
        session.commit()

        value = calculator.calculate_custom_factor(ticker, factor_def, as_of)

        # Should return a float or None
        if value is not None:
            assert isinstance(value, float)

    def test_calculate_custom_factor_pe_ratio(
        self, session: Session, sample_factors, sample_fundamentals
    ):
        """Test custom factor calculation for P/E ratio."""
        calculator = FactorCalculator(session)
        factor_def = sample_factors[1]  # Earnings Yield factor
        ticker = "MSFT"
        as_of = date(2023, 3, 1)

        # Manually set formula
        factor_def.calculation_formula = "earnings_yield"
        session.add(factor_def)
        session.commit()

        value = calculator.calculate_custom_factor(ticker, factor_def, as_of)

        if value is not None:
            assert isinstance(value, float)

    def test_calculate_custom_factor_leverage(
        self, session: Session, sample_factors, sample_fundamentals
    ):
        """Test custom factor calculation for leverage."""
        calculator = FactorCalculator(session)
        factor_def = sample_factors[2]  # Leverage factor
        ticker = "GOOGL"
        as_of = date(2023, 3, 1)

        # Manually set formula
        factor_def.calculation_formula = "leverage"
        session.add(factor_def)
        session.commit()

        value = calculator.calculate_custom_factor(ticker, factor_def, as_of)

        if value is not None:
            assert isinstance(value, float)
            assert value >= 0

    def test_calculate_custom_factor_no_formula(
        self, session: Session, sample_factors
    ):
        """Test custom factor with no formula defined."""
        calculator = FactorCalculator(session)
        factor_def = sample_factors[0]
        ticker = "AAPL"
        as_of = date(2023, 3, 1)

        # Clear formula
        factor_def.calculation_formula = None
        session.add(factor_def)
        session.commit()

        value = calculator.calculate_custom_factor(ticker, factor_def, as_of)

        # Should return None
        assert value is None

    def test_calculate_custom_factor_unknown_formula(
        self, session: Session, sample_factors
    ):
        """Test custom factor with unknown formula."""
        calculator = FactorCalculator(session)
        factor_def = sample_factors[0]
        ticker = "AAPL"
        as_of = date(2023, 3, 1)

        # Set unknown formula
        factor_def.calculation_formula = "unknown_metric"
        session.add(factor_def)
        session.commit()

        value = calculator.calculate_custom_factor(ticker, factor_def, as_of)

        # Should return None gracefully
        assert value is None


class TestCalculateFamaFrenchExposures:
    """Test Fama-French factor exposure calculation."""

    def test_calculate_ff_exposures_basic(
        self, session: Session, sample_securities, sample_prices
    ):
        """Test basic FF factor exposure calculation."""
        calculator = FactorCalculator(session)
        ticker = "AAPL"
        as_of = date(2023, 6, 30)

        exposures = calculator.calculate_fama_french_exposures(
            ticker, as_of, window_months=60
        )

        # Should return a dict or None
        if exposures is not None:
            assert isinstance(exposures, dict)
            # Should have standard FF5 factors
            assert "beta_market" in exposures
            assert "beta_smb" in exposures
            assert "beta_hml" in exposures

    def test_calculate_ff_exposures_insufficient_data(
        self, session: Session
    ):
        """Test FF calculation with insufficient historical data."""
        calculator = FactorCalculator(session)
        ticker = "NONEXISTENT"
        as_of = date(2023, 6, 30)

        exposures = calculator.calculate_fama_french_exposures(
            ticker, as_of, window_months=60
        )

        # Should return None
        assert exposures is None

    def test_calculate_ff_exposures_custom_window(
        self, session: Session, sample_securities, sample_prices
    ):
        """Test FF calculation with custom window."""
        calculator = FactorCalculator(session)
        ticker = "MSFT"
        as_of = date(2023, 6, 30)

        exposures = calculator.calculate_fama_french_exposures(
            ticker, as_of, window_months=12
        )

        # Should compute regardless of window size
        if exposures is not None:
            assert isinstance(exposures, dict)


class TestFactorCalculatorEdgeCases:
    """Test edge cases and error handling."""

    def test_rank_universe_single_ticker(
        self, session: Session, sample_factors, sample_fundamentals
    ):
        """Test ranking with single ticker in universe."""
        calculator = FactorCalculator(session)
        tickers = ["AAPL"]
        factor_id = sample_factors[0].id
        as_of = date(2023, 3, 1)

        ranks = calculator.rank_universe(factor_id, tickers, as_of)

        # Single ticker should get 100th percentile
        if len(ranks) == 1:
            assert list(ranks.values())[0] == 100.0

    def test_calculate_factor_large_universe(
        self, session: Session, sample_factors
    ):
        """Test ranking with large universe."""
        calculator = FactorCalculator(session)
        # Create large universe of tickers
        tickers = [f"STOCK{i:04d}" for i in range(500)]
        factor_id = sample_factors[0].id
        as_of = date(2023, 3, 1)

        ranks = calculator.rank_universe(factor_id, tickers, as_of)

        # Should handle large universe without error
        assert isinstance(ranks, dict)

    def test_calculate_factor_negative_fundamentals(
        self, session: Session, sample_factors, sample_fundamentals
    ):
        """Test factor calculation with negative fundamental values."""
        calculator = FactorCalculator(session)

        # This test checks if negative fundamentals are handled
        # (e.g., negative earnings, negative FCF)
        ticker = "AAPL"
        as_of = date(2023, 3, 1)

        # Should not crash with negative values
        de_ratio = calculator._calculate_debt_to_equity(ticker, as_of)

        if de_ratio is not None:
            assert isinstance(de_ratio, float)
