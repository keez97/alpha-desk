"""
SmartEstimate Engine - Weighted analyst consensus calculation and signal generation.

Implements recency decay, accuracy tier weighting, and divergence-based signals
for earnings surprise prediction.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import math
import logging
from sqlmodel import Session

from backend.repositories.earnings_repo import EarningsRepository
from backend.services.data_provider import get_fundamentals as get_stock_fundamentals

logger = logging.getLogger(__name__)

# Default weight parameters
DEFAULT_WEIGHTS = {
    "recency_decay": {
        "half_life_days": Decimal("30"),  # ln(2) decay with 30-day half-life
    },
    "accuracy_tier": {
        "tier_a_weight": Decimal("1.5"),  # Top quartile
        "tier_b_weight": Decimal("1.0"),  # Mid tiers
        "tier_c_weight": Decimal("0.5"),  # Bottom quartile
    },
}


class SmartEstimateEngine:
    """SmartEstimate calculation engine."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = EarningsRepository(session)

    def calculate_smart_estimate(
        self,
        ticker: str,
        fiscal_quarter: str,
    ) -> Dict[str, Any]:
        """
        Calculate weighted analyst consensus using recency decay and accuracy tiers.

        Process:
        1. Get all estimates for (ticker, quarter) from earnings_estimate table
        2. Apply recency decay: weight = exp(-lambda * days_since_estimate)
           where lambda = ln(2) / half_life_days
        3. Apply accuracy tier: A-tier = 1.5x, B-tier = 1.0x, C-tier = 0.5x
        4. Normalize weights to sum to 1
        5. Weighted average of eps_estimate values = SmartEstimate
        6. Compare to simple consensus (unweighted average)
        7. Return: smart_eps, consensus_eps, divergence_pct, signal

        Args:
            ticker: Security ticker
            fiscal_quarter: Fiscal quarter in format YYYYQ#

        Returns:
            Dictionary with:
            - smart_eps: Weighted SmartEstimate EPS
            - consensus_eps: Unweighted consensus EPS
            - divergence_pct: (smart - consensus) / abs(consensus) * 100
            - signal: 'buy' if smart > consensus, 'sell' if smart < consensus, else 'hold'
            - num_estimates: Count of estimates used
            - details: Additional weighting details
        """
        # Get all individual estimates
        estimates = self.repo.get_estimates(
            ticker,
            fiscal_quarter,
            estimate_type="individual",
        )

        if not estimates:
            logger.warning(f"No estimates found for {ticker} {fiscal_quarter}")
            return {
                "smart_eps": None,
                "consensus_eps": None,
                "divergence_pct": None,
                "signal": "hold",
                "num_estimates": 0,
                "error": "No estimates available",
            }

        # Get weights configuration
        weights = self.repo.get_weights()
        half_life = self._get_weight_param(weights, "recency_decay", "half_life_days")

        now = datetime.now(timezone.utc)
        weighted_sum = Decimal("0")
        weight_sum = Decimal("0")
        eps_values = []
        weight_details = []

        # Calculate weights and apply them
        for estimate in estimates:
            eps_values.append(float(estimate.eps_estimate))

            # 1. Recency decay
            days_since = (now - estimate.estimate_date).days
            lambda_param = Decimal(math.log(2)) / half_life
            recency_weight = Decimal(str(math.exp(-float(lambda_param) * days_since)))

            # 2. Accuracy tier - get from analyst scorecard
            scorecard = None
            if estimate.analyst_broker:
                scorecards = self.repo.get_scorecards(broker=estimate.analyst_broker, ticker=ticker)
                if scorecards:
                    scorecard = scorecards[0]

            tier_weight = self._get_tier_weight(scorecard, weights)

            # 3. Combined weight
            total_weight = recency_weight * tier_weight
            weighted_sum += estimate.eps_estimate * total_weight
            weight_sum += total_weight

            weight_details.append({
                "analyst": estimate.analyst_broker or "unknown",
                "eps_estimate": float(estimate.eps_estimate),
                "recency_weight": float(recency_weight),
                "tier_weight": float(tier_weight),
                "total_weight": float(total_weight),
            })

        # Normalize weights and calculate smart estimate
        if weight_sum == 0:
            logger.warning(f"Weight sum is zero for {ticker} {fiscal_quarter}")
            return {
                "smart_eps": None,
                "consensus_eps": None,
                "divergence_pct": None,
                "signal": "hold",
                "num_estimates": 0,
                "error": "Weight calculation error",
            }

        smart_eps = weighted_sum / weight_sum

        # Simple consensus (unweighted average)
        consensus_eps = Decimal(sum(eps_values)) / len(eps_values) if eps_values else None

        # Calculate divergence
        divergence_pct = None
        if consensus_eps and consensus_eps != 0:
            divergence_pct = ((smart_eps - consensus_eps) / abs(consensus_eps)) * Decimal("100")

        return {
            "smart_eps": float(smart_eps),
            "consensus_eps": float(consensus_eps) if consensus_eps else None,
            "divergence_pct": float(divergence_pct) if divergence_pct else None,
            "signal": "hold",  # Will be updated by generate_signal
            "num_estimates": len(estimates),
            "details": weight_details,
        }

    def generate_signal(
        self,
        divergence_pct: float,
        direction: str = "unknown",
        smart_eps: Optional[float] = None,
        consensus_eps: Optional[float] = None,
    ) -> Tuple[str, int]:
        """
        Generate trading signal based on estimate divergence.

        Rules:
        - If |divergence| >= 2% and smart > consensus: 'buy' signal
        - If |divergence| >= 2% and smart < consensus: 'sell' signal
        - Otherwise: 'hold' signal
        - Confidence increases with magnitude: 50 + (magnitude - 2) * 10, capped at 100

        Args:
            divergence_pct: Divergence percentage
            direction: Direction hint ('positive', 'negative', 'unknown')
            smart_eps: SmartEstimate EPS (for verification)
            consensus_eps: Consensus EPS (for verification)

        Returns:
            Tuple of (signal_type, confidence) where:
            - signal_type: 'buy', 'sell', or 'hold'
            - confidence: 0-100 integer
        """
        if divergence_pct is None or abs(divergence_pct) < 2.0:
            return ("hold", 50)

        # Determine direction
        if smart_eps is not None and consensus_eps is not None:
            is_smart_higher = smart_eps > consensus_eps
        else:
            is_smart_higher = divergence_pct > 0

        signal_type = "buy" if is_smart_higher else "sell"

        # Calculate confidence based on magnitude
        magnitude = abs(divergence_pct)
        base_confidence = 50
        incremental_confidence = min((magnitude - 2.0) * 10, 50)  # Cap at 50 additional
        confidence = int(base_confidence + incremental_confidence)

        return (signal_type, min(confidence, 100))

    def refresh_estimates(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Pull latest estimates from yfinance for all tickers.

        Note: yfinance provides consensus estimates through the earnings_estimate endpoint.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with refresh statistics
        """
        import yfinance as yf

        stats = {
            "total_tickers": len(tickers),
            "estimates_refreshed": 0,
            "errors": [],
        }

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                earnings_estimate = stock.earnings_estimate

                if earnings_estimate is None or earnings_estimate.empty:
                    stats["errors"].append(f"{ticker}: No earnings estimates available")
                    continue

                # yfinance provides estimates as a DataFrame with fiscal quarters as index
                for fiscal_quarter_str, row in earnings_estimate.iterrows():
                    if row.isna().all():
                        continue

                    # Convert yfinance quarter format to our format if needed
                    # yfinance uses format like "2025-12-31" for quarter end dates
                    fiscal_quarter = self._yfinance_quarter_to_format(fiscal_quarter_str)

                    # Get consensus estimate
                    consensus_estimate = row.get("Earnings Estimate", None)

                    if consensus_estimate and not math.isnan(consensus_estimate):
                        self.repo.save_estimate(
                            ticker=ticker,
                            fiscal_quarter=fiscal_quarter,
                            estimate_type="consensus",
                            eps_estimate=Decimal(str(consensus_estimate)),
                            estimate_date=datetime.now(timezone.utc),
                            analyst_broker=None,
                        )
                        stats["estimates_refreshed"] += 1

            except Exception as e:
                logger.error(f"Error refreshing estimates for {ticker}: {e}")
                stats["errors"].append(f"{ticker}: {str(e)}")

        return stats

    def update_scorecards(self) -> Dict[str, Any]:
        """
        Update analyst accuracy tiers after earnings are reported.

        Compares estimates to actuals and calculates:
        - Percentage within ±5% of actual
        - Directional accuracy
        - Average error percentage

        Returns:
            Dictionary with update statistics
        """
        stats = {
            "scorecards_updated": 0,
            "estimates_evaluated": 0,
            "errors": [],
        }

        # Get all reported earnings
        query = "SELECT DISTINCT analyst_broker FROM earnings_estimate WHERE analyst_broker IS NOT NULL"

        try:
            # Get unique brokers
            from sqlmodel import select
            from backend.models.earnings import EarningsEstimate

            brokers = self.session.exec(
                select(EarningsEstimate.analyst_broker).distinct()
                .where(EarningsEstimate.analyst_broker.isnot(None))
            ).all()

            for broker in brokers:
                if not broker:
                    continue

                # Get all estimates from this broker
                estimates = self.session.exec(
                    select(EarningsEstimate).where(
                        EarningsEstimate.analyst_broker == broker,
                        EarningsEstimate.estimate_type == "individual",
                    )
                ).all()

                total_estimates = 0
                accurate_count = 0
                errors = []

                for estimate in estimates:
                    actual = self.repo.get_actual(estimate.ticker, estimate.fiscal_quarter)
                    if not actual:
                        continue

                    if actual.actual_eps == 0 or estimate.eps_estimate is None:
                        continue

                    total_estimates += 1
                    error_pct = abs((estimate.eps_estimate - actual.actual_eps) / actual.actual_eps * 100)
                    errors.append(float(error_pct))

                    if error_pct <= 5.0:
                        accurate_count += 1

                if total_estimates > 0:
                    avg_error = sum(errors) / len(errors)
                    directional_accuracy = accurate_count / total_estimates * 100

                    # Determine which direction (within stock)
                    self.repo.save_analyst_scorecard(
                        analyst_broker=broker,
                        total_estimates=total_estimates,
                        accurate_count=accurate_count,
                        directional_accuracy=Decimal(str(directional_accuracy)),
                        avg_error_pct=Decimal(str(avg_error)),
                        ticker=None,  # Aggregate across all stocks
                    )

                    stats["scorecards_updated"] += 1
                    stats["estimates_evaluated"] += total_estimates

        except Exception as e:
            logger.error(f"Error updating scorecards: {e}")
            stats["errors"].append(str(e))

        return stats

    # ==================== Private Helpers ====================

    def _get_weight_param(
        self,
        weights: List,
        weight_type: str,
        param_name: str,
    ) -> Decimal:
        """Get a weight parameter value from the database."""
        for w in weights:
            if w.weight_type == weight_type and w.parameter_name == param_name:
                return w.parameter_value

        # Return default
        if weight_type == "recency_decay" and param_name == "half_life_days":
            return Decimal("30")
        return Decimal("1")

    def _get_tier_weight(
        self,
        scorecard,
        weights: List,
    ) -> Decimal:
        """Determine analyst tier weight based on accuracy."""
        if not scorecard or not scorecard.avg_error_pct:
            return Decimal("1.0")  # Default to B-tier

        error = float(scorecard.avg_error_pct)

        # Determine tier based on error percentile
        if error <= 3.0:  # Top quartile
            return self._get_weight_param(weights, "accuracy_tier", "tier_a_weight")
        elif error <= 5.0:  # Mid quartiles
            return self._get_weight_param(weights, "accuracy_tier", "tier_b_weight")
        else:  # Bottom quartile
            return self._get_weight_param(weights, "accuracy_tier", "tier_c_weight")

    def _yfinance_quarter_to_format(self, yfinance_quarter: str) -> str:
        """
        Convert yfinance quarter format to YYYYQ# format.

        Args:
            yfinance_quarter: Format like "2025-12-31" or "2025Q4"

        Returns:
            Format like "2025Q4"
        """
        try:
            # Try parsing as date (yfinance sometimes returns dates)
            from datetime import datetime as dt
            parsed = dt.strptime(str(yfinance_quarter).split()[0], "%Y-%m-%d")
            month = parsed.month
            year = parsed.year

            # Determine quarter from month
            quarter = (month - 1) // 3 + 1
            return f"{year}Q{quarter}"
        except:
            # Already in YYYYQ# format or unparseable
            return str(yfinance_quarter)
