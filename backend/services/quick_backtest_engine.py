"""
Quick backtest engine for generating pre-configured backtests from RRG positioning.
Generates backtest parameters based on sector quadrant and momentum.
"""

from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class QuickBacktestEngine:
    """Service for generating quick backtest configurations from RRG data."""

    # Standard transaction costs
    COMMISSION_BPS = 10
    SLIPPAGE_BPS = 5

    # Lookback period in months
    LOOKBACK_MONTHS = 6

    # Trade direction mapping from quadrants
    QUADRANT_MAPPING = {
        "Strengthening": ("long", "high"),      # High RS, rising momentum
        "Weakening": ("short", "medium"),        # High RS, falling momentum
        "Recovering": ("long", "medium"),        # Low RS, rising momentum
        "Deteriorating": ("short", "low"),       # Low RS, falling momentum
    }

    @staticmethod
    def generate_trade_idea(
        ticker: str,
        sector_name: str,
        quadrant: str,
        rs_ratio: float,
        rs_momentum: float,
    ) -> Dict[str, Any]:
        """
        Generate a trade idea based on RRG quadrant.

        Args:
            ticker: Sector ETF ticker (e.g., XLU, XLK)
            sector_name: Human-readable sector name
            quadrant: RRG quadrant (Strengthening, Weakening, Recovering, Deteriorating)
            rs_ratio: Current RS-Ratio value
            rs_momentum: Current RS-Momentum value

        Returns:
            Dictionary with trade direction, thesis, and suggested pair
        """
        direction, confidence = QuickBacktestEngine.QUADRANT_MAPPING.get(
            quadrant, ("avoid", "low")
        )

        thesis_map = {
            "Strengthening": "Sector showing relative strength with positive momentum. Ride the trend of strength and outperformance.",
            "Weakening": "Sector outperforming but momentum fading. Exit before rotation turns negative.",
            "Recovering": "Sector was lagging but turning up. Catch the early rotation from underperformance to outperformance.",
            "Deteriorating": "Sector weak with deteriorating momentum. Avoid or short until momentum stabilizes.",
        }

        thesis = thesis_map.get(quadrant, "Monitor for trend change")

        # Suggest pair trades for directional strategies
        suggested_pair = None
        if direction == "long":
            suggested_pair = "SPY"  # Long sector, short market as hedge
        elif direction == "short":
            suggested_pair = "SPY"  # Short sector, long market as hedge

        return {
            "ticker": ticker,
            "sectorName": sector_name,
            "quadrant": quadrant,
            "direction": direction,
            "thesis": thesis,
            "suggestedPairTicker": suggested_pair,
            "confidence": confidence,
            "rsRatio": float(rs_ratio),
            "rsMomentum": float(rs_momentum),
        }

    @staticmethod
    def generate_backtest_config(
        ticker: str,
        sector_name: str,
        quadrant: str,
        rs_ratio: float,
        rs_momentum: float,
        end_date: Optional[date] = None,
        trade_type: str = "single",
        short_ticker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a pre-configured backtest from RRG positioning.

        Args:
            ticker: Long leg ticker
            sector_name: Sector name for naming
            quadrant: RRG quadrant
            rs_ratio: Current RS-Ratio
            rs_momentum: Current RS-Momentum
            end_date: End date (default: today)
            trade_type: "single" or "pair"
            short_ticker: Short leg for pair trades

        Returns:
            Pre-filled backtest configuration
        """
        if end_date is None:
            end_date = date.today()

        # Calculate start date (6 months back)
        start_date = end_date - timedelta(days=30 * QuickBacktestEngine.LOOKBACK_MONTHS)

        # Get trade direction and generate name
        direction, confidence = QuickBacktestEngine.QUADRANT_MAPPING.get(
            quadrant, ("avoid", "low")
        )

        # Generate sensible name
        direction_name = (
            "Long" if direction == "long" else "Short" if direction == "short" else "Monitor"
        )
        name = f"{direction_name} {ticker} {quadrant} Play - {end_date.strftime('%Y-%m-%d')}"

        # For pair trades, adjust name
        if trade_type == "pair" and short_ticker:
            name = f"Long {ticker}/Short {short_ticker} Pair - {end_date.strftime('%Y-%m-%d')}"

        # Define factor allocations based on trade direction
        # For now, use equal-weight single sector trade or simple pair allocation
        if trade_type == "single":
            # Single sector: long=100% in sector, short=0% (underweight)
            if direction == "long":
                factor_allocations = {"sector": 1.0}
            else:
                factor_allocations = {"sector": 0.0}
        else:
            # Pair trade: equal weight long and short
            factor_allocations = {
                "long_sector": 0.5,
                "short_sector": 0.5,
            }

        return {
            "name": name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "rebalance_frequency": "monthly",
            "transaction_costs": {
                "commission_bps": QuickBacktestEngine.COMMISSION_BPS,
                "slippage_bps": QuickBacktestEngine.SLIPPAGE_BPS,
            },
            "universe_selection": "sp500",
            "factor_allocations": factor_allocations,
            "ticker": ticker,
            "short_ticker": short_ticker,
            "trade_type": trade_type,
            "direction": direction,
            "quadrant": quadrant,
            "confidence": confidence,
        }

    @staticmethod
    def generate_trade_ideas_for_sectors(
        sectors_data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate trade ideas for all sectors based on RRG positioning.

        Args:
            sectors_data: List of sector data with ticker, name, quadrant, etc.

        Returns:
            List of trade ideas sorted by confidence
        """
        trade_ideas = []

        for sector in sectors_data:
            try:
                idea = QuickBacktestEngine.generate_trade_idea(
                    ticker=sector.get("ticker", ""),
                    sector_name=sector.get("name", sector.get("sector", "")),
                    quadrant=sector.get("quadrant", "Unknown"),
                    rs_ratio=sector.get("rs_ratio", 100),
                    rs_momentum=sector.get("rs_momentum", 0),
                )

                # Generate backtest config
                config = QuickBacktestEngine.generate_backtest_config(
                    ticker=idea["ticker"],
                    sector_name=idea["sectorName"],
                    quadrant=idea["quadrant"],
                    rs_ratio=idea["rsRatio"],
                    rs_momentum=idea["rsMomentum"],
                )

                # Combine into full trade idea with config
                full_idea = {**idea, "backtestConfig": config}
                trade_ideas.append(full_idea)

            except Exception as e:
                logger.warning(f"Error generating trade idea for {sector.get('ticker')}: {e}")
                continue

        # Sort by confidence (high > medium > low)
        confidence_order = {"high": 0, "medium": 1, "low": 2}
        trade_ideas.sort(
            key=lambda x: (
                confidence_order.get(x.get("confidence", "low"), 3),
                x.get("ticker", ""),
            )
        )

        return trade_ideas
