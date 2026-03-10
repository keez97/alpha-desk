"""
Earnings Data Service - Data ingestion for estimates and actuals.

Pulls analyst estimates and actual earnings from yfinance and manages
the ingestion pipeline for the Earnings Surprise Predictor.
"""

from datetime import datetime, timezone, date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
import logging
import yfinance as yf
import math

from sqlmodel import Session

from backend.repositories.earnings_repo import EarningsRepository
from backend.services.smart_estimate_engine import SmartEstimateEngine

logger = logging.getLogger(__name__)


class EarningsDataService:
    """Service for ingesting earnings data."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = EarningsRepository(session)
        self.engine = SmartEstimateEngine(session)

    def ingest_estimates(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Pull analyst estimates from yfinance.

        yfinance provides consensus earnings estimates through the earnings_estimate
        endpoint. This method fetches them and stores in earnings_estimate table.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            "total_tickers": len(tickers),
            "estimates_ingested": 0,
            "quarters_processed": 0,
            "errors": [],
        }

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)

                # Get earnings dates first
                calendar = stock.calendar
                if calendar is None or calendar.empty:
                    logger.info(f"No earnings calendar for {ticker}")
                    continue

                # yfinance.calendar has format:
                # - index: dates
                # - 'Earnings Date': date of earnings
                # - 'Earnings Average': consensus estimate
                # - 'Report Date': date of report

                for idx, row in calendar.iterrows():
                    try:
                        earnings_date = row.get("Earnings Date")
                        earnings_avg = row.get("Earnings Average")

                        if earnings_avg is None or (isinstance(earnings_avg, float) and math.isnan(earnings_avg)):
                            continue

                        # Convert date to fiscal quarter
                        if isinstance(earnings_date, str):
                            earnings_date = datetime.fromisoformat(earnings_date.split()[0]).date()

                        fiscal_quarter = self._date_to_fiscal_quarter(earnings_date)

                        # Check if we already have a recent estimate
                        existing = self.repo.get_latest_consensus(ticker, fiscal_quarter)
                        if existing and (datetime.now(timezone.utc) - existing.estimate_date).days < 1:
                            # Already have fresh data
                            continue

                        # Save consensus estimate
                        self.repo.save_estimate(
                            ticker=ticker,
                            fiscal_quarter=fiscal_quarter,
                            estimate_type="consensus",
                            eps_estimate=Decimal(str(earnings_avg)),
                            estimate_date=datetime.now(timezone.utc),
                            analyst_broker=None,
                        )

                        stats["estimates_ingested"] += 1
                        stats["quarters_processed"] += 1

                    except Exception as e:
                        logger.warning(f"Error processing earnings estimate for {ticker}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error ingesting estimates for {ticker}: {e}")
                stats["errors"].append(f"{ticker}: {str(e)}")

        return stats

    def ingest_actuals(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Pull actual reported earnings from yfinance.

        After earnings announcement, yfinance provides actual EPS and calculates
        the surprise versus consensus estimates.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            "total_tickers": len(tickers),
            "actuals_ingested": 0,
            "errors": [],
        }

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)

                # Get earnings history (actual vs estimate)
                earnings_history = stock.quarterly_earnings

                if earnings_history is None or earnings_history.empty:
                    logger.info(f"No earnings history for {ticker}")
                    continue

                # yfinance.quarterly_earnings has columns:
                # - Date: earnings announcement date
                # - EPS Estimate: consensus estimate
                # - Reported EPS: actual EPS
                # - Surprise %: (actual - estimate) / estimate

                for idx, row in earnings_history.iterrows():
                    try:
                        report_date = idx if isinstance(idx, date) else row.get("Date")
                        if isinstance(report_date, str):
                            report_date = datetime.fromisoformat(report_date.split()[0]).date()

                        actual_eps = row.get("Reported EPS")
                        eps_estimate = row.get("EPS Estimate")
                        surprise_pct = row.get("Surprise %")

                        if actual_eps is None or (isinstance(actual_eps, float) and math.isnan(actual_eps)):
                            continue

                        # Determine fiscal quarter
                        fiscal_quarter = self._date_to_fiscal_quarter(report_date)

                        # Check if we already have this actual
                        existing = self.repo.get_actual(ticker, fiscal_quarter)
                        if existing:
                            # Already ingested
                            continue

                        # Convert surprise from percentage to decimal if provided
                        surprise_vs_consensus = None
                        if surprise_pct and not math.isnan(surprise_pct):
                            surprise_vs_consensus = Decimal(str(surprise_pct))

                        # Save actual
                        self.repo.save_actual(
                            ticker=ticker,
                            fiscal_quarter=fiscal_quarter,
                            actual_eps=Decimal(str(actual_eps)),
                            report_date=report_date,
                            report_time=self._infer_report_time(row),
                            surprise_vs_consensus=surprise_vs_consensus,
                            source="yfinance",
                        )

                        stats["actuals_ingested"] += 1

                    except Exception as e:
                        logger.warning(f"Error processing actual earnings for {ticker}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error ingesting actuals for {ticker}: {e}")
                stats["errors"].append(f"{ticker}: {str(e)}")

        return stats

    def get_upcoming_earnings(
        self,
        tickers: Optional[List[str]] = None,
        days_ahead: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming earnings dates and estimates.

        Args:
            tickers: Optional list of specific tickers (default: all in database)
            days_ahead: Number of days ahead to look (default 30)

        Returns:
            List of dictionaries with upcoming earnings data
        """
        upcoming = []
        today = date.today()
        future_date = today + timedelta(days=days_ahead)

        # If no tickers specified, get from calendar
        if not tickers:
            # Use repo method
            return self.repo.get_earnings_calendar(days_ahead=days_ahead)

        # Fetch for specified tickers
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                calendar = stock.calendar

                if calendar is None or calendar.empty:
                    continue

                for idx, row in calendar.iterrows():
                    try:
                        earnings_date_str = row.get("Earnings Date")
                        earnings_avg = row.get("Earnings Average")

                        if earnings_date_str is None:
                            continue

                        if isinstance(earnings_date_str, str):
                            earnings_date = datetime.fromisoformat(earnings_date_str.split()[0]).date()
                        else:
                            earnings_date = earnings_date_str

                        # Only include upcoming earnings
                        if earnings_date < today or earnings_date > future_date:
                            continue

                        fiscal_quarter = self._date_to_fiscal_quarter(earnings_date)
                        days_to_earnings = (earnings_date - today).days

                        upcoming.append({
                            "ticker": ticker,
                            "earnings_date": earnings_date.isoformat(),
                            "fiscal_quarter": fiscal_quarter,
                            "consensus_eps": float(earnings_avg) if earnings_avg and not math.isnan(earnings_avg) else None,
                            "days_to_earnings": days_to_earnings,
                        })

                    except Exception as e:
                        logger.warning(f"Error processing earnings date for {ticker}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error fetching earnings for {ticker}: {e}")

        # Sort by earnings date
        upcoming.sort(key=lambda x: x["earnings_date"])

        return upcoming

    def refresh_all_estimates(self, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Full refresh of estimates for all or specified tickers.

        Args:
            tickers: Optional list of specific tickers to refresh

        Returns:
            Dictionary with refresh statistics
        """
        if not tickers:
            # Get all tickers from database
            from sqlmodel import select
            from backend.models.securities import Security

            tickers = self.session.exec(select(Security.ticker)).all()

        # Ingest estimates and actuals
        estimate_stats = self.ingest_estimates(tickers)
        actual_stats = self.ingest_actuals(tickers)

        # Generate SmartEstimates
        smart_estimate_stats = self._generate_smart_estimates(tickers)

        # Update analyst scorecards
        scorecard_stats = self.engine.update_scorecards()

        return {
            "estimates": estimate_stats,
            "actuals": actual_stats,
            "smart_estimates": smart_estimate_stats,
            "scorecards": scorecard_stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ==================== Private Helpers ====================

    def _date_to_fiscal_quarter(self, d: date) -> str:
        """
        Convert date to fiscal quarter format YYYYQ#.

        Assumes calendar quarters aligned with year.

        Args:
            d: Date object

        Returns:
            Fiscal quarter string like "2025Q4"
        """
        month = d.month
        year = d.year
        quarter = (month - 1) // 3 + 1
        return f"{year}Q{quarter}"

    def _infer_report_time(self, row: Dict[str, Any]) -> Optional[str]:
        """
        Infer earnings report time from available data.

        Args:
            row: Row from yfinance earnings data

        Returns:
            'pre_market', 'post_market', 'during', or None
        """
        # yfinance doesn't directly provide report time, so return None
        # This could be enhanced with a more sophisticated heuristic
        return None

    def _generate_smart_estimates(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Generate SmartEstimates for all upcoming quarters.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with SmartEstimate generation statistics
        """
        stats = {
            "total_tickers": len(tickers),
            "smart_estimates_generated": 0,
            "errors": [],
        }

        # Get all unique fiscal quarters with estimates
        from sqlmodel import select
        from backend.models.earnings import EarningsEstimate

        quarters = self.session.exec(
            select(EarningsEstimate.fiscal_quarter).distinct()
            .where(EarningsEstimate.estimate_type == "individual")
        ).all()

        for ticker in tickers:
            for quarter in quarters:
                try:
                    # Calculate SmartEstimate
                    smart_est = self.engine.calculate_smart_estimate(ticker, quarter)

                    if smart_est.get("smart_eps") is None:
                        continue

                    # Check if we already have a SmartEstimate for this quarter
                    existing = self.repo.get_estimates(
                        ticker,
                        quarter,
                        estimate_type="smart_estimate",
                    )

                    if existing:
                        # Update with new calculation
                        continue

                    # Save SmartEstimate
                    self.repo.save_estimate(
                        ticker=ticker,
                        fiscal_quarter=quarter,
                        estimate_type="smart_estimate",
                        eps_estimate=Decimal(str(smart_est["smart_eps"])),
                        estimate_date=datetime.now(timezone.utc),
                    )

                    # Generate signal
                    divergence_pct = smart_est.get("divergence_pct")
                    if divergence_pct and abs(divergence_pct) >= 2.0:
                        signal_type, confidence = self.engine.generate_signal(
                            divergence_pct,
                            smart_eps=smart_est.get("smart_eps"),
                            consensus_eps=smart_est.get("consensus_eps"),
                        )

                        # Determine days to earnings (estimate)
                        days_to_earnings = 30  # Default estimate

                        # Save signal
                        self.repo.save_signal(
                            ticker=ticker,
                            fiscal_quarter=quarter,
                            signal_date=datetime.now(timezone.utc),
                            signal_type=signal_type,
                            confidence=confidence,
                            smart_estimate_eps=Decimal(str(smart_est["smart_eps"])),
                            consensus_eps=Decimal(str(smart_est["consensus_eps"])),
                            divergence_pct=Decimal(str(divergence_pct)),
                            days_to_earnings=days_to_earnings,
                            valid_until=datetime.now(timezone.utc) + timedelta(days=days_to_earnings),
                        )

                    stats["smart_estimates_generated"] += 1

                except Exception as e:
                    logger.warning(f"Error generating SmartEstimate for {ticker} {quarter}: {e}")
                    stats["errors"].append(f"{ticker} {quarter}: {str(e)}")

        return stats
