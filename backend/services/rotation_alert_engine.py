"""
Rotation Alert Engine - detects RRG quadrant boundary crossings and momentum changes.

Compares current RRG positions with historical trail data to identify:
- Quadrant changes (sector moving between quadrants)
- Momentum reversals (RS-Momentum sign change)
- Breakouts (RS-Ratio crossing above 100 with positive momentum)
- Breakdowns (RS-Ratio crossing below 100 with negative momentum)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RotationAlertEngine:
    """Stateless engine for detecting rotation alerts from RRG data."""

    @staticmethod
    def detect_alerts(rrg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect rotation alerts from RRG calculation results.

        Args:
            rrg_data: Result from calculate_rrg() containing sectors with trail history

        Returns:
            List of alert dicts with keys: ticker, sector, alert_type, from_quadrant,
            to_quadrant, rs_ratio, rs_momentum, description, severity
        """
        alerts = []
        sectors = rrg_data.get("sectors", [])

        for sector in sectors:
            ticker = sector.get("ticker")
            sector_name = sector.get("sector")
            current_quadrant = sector.get("quadrant")
            current_rs_ratio = sector.get("rs_ratio")
            current_rs_momentum = sector.get("rs_momentum")
            trail = sector.get("trail", [])

            if not trail or len(trail) < 2:
                continue

            # Get previous values from trail (1 week ago)
            # Trail is ordered chronologically, latest is at end
            prev_entry = trail[-2] if len(trail) >= 2 else None
            curr_entry = trail[-1]

            if not prev_entry:
                continue

            prev_rs_ratio = prev_entry.get("rs_ratio")
            prev_rs_momentum = prev_entry.get("rs_momentum")

            # Determine previous quadrant
            prev_quadrant = RotationAlertEngine._determine_quadrant(
                prev_rs_ratio, prev_rs_momentum
            )

            # Check for quadrant change
            if current_quadrant != prev_quadrant:
                alert = RotationAlertEngine._create_quadrant_change_alert(
                    ticker,
                    sector_name,
                    prev_quadrant,
                    current_quadrant,
                    current_rs_ratio,
                    current_rs_momentum,
                )
                if alert:
                    alerts.append(alert)

            # Check for momentum reversal
            if RotationAlertEngine._is_momentum_reversal(
                prev_rs_momentum, current_rs_momentum
            ):
                alert = RotationAlertEngine._create_momentum_reversal_alert(
                    ticker,
                    sector_name,
                    current_rs_ratio,
                    current_rs_momentum,
                    prev_rs_momentum,
                )
                alerts.append(alert)

            # Check for breakout (RS-Ratio crossing above 100)
            if RotationAlertEngine._is_breakout(prev_rs_ratio, current_rs_ratio, current_rs_momentum):
                alert = RotationAlertEngine._create_breakout_alert(
                    ticker, sector_name, current_rs_ratio, current_rs_momentum
                )
                alerts.append(alert)

            # Check for breakdown (RS-Ratio crossing below 100)
            if RotationAlertEngine._is_breakdown(prev_rs_ratio, current_rs_ratio, current_rs_momentum):
                alert = RotationAlertEngine._create_breakdown_alert(
                    ticker, sector_name, current_rs_ratio, current_rs_momentum
                )
                alerts.append(alert)

        return alerts

    @staticmethod
    def _determine_quadrant(rs_ratio: float, rs_momentum: float) -> str:
        """Determine RRG quadrant from RS-Ratio and RS-Momentum."""
        above_100 = rs_ratio > 100
        positive_momentum = rs_momentum > 0

        if above_100 and positive_momentum:
            return "Strengthening"
        elif above_100 and not positive_momentum:
            return "Weakening"
        elif not above_100 and positive_momentum:
            return "Recovering"
        else:
            return "Deteriorating"

    @staticmethod
    def _is_momentum_reversal(prev_momentum: float, curr_momentum: float) -> bool:
        """Check if momentum changed sign."""
        if prev_momentum == 0 or curr_momentum == 0:
            return False
        return (prev_momentum > 0 and curr_momentum < 0) or (
            prev_momentum < 0 and curr_momentum > 0
        )

    @staticmethod
    def _is_breakout(
        prev_rs_ratio: float, curr_rs_ratio: float, curr_momentum: float
    ) -> bool:
        """Check if RS-Ratio crossed above 100 with positive momentum."""
        return prev_rs_ratio <= 100 and curr_rs_ratio > 100 and curr_momentum > 0

    @staticmethod
    def _is_breakdown(
        prev_rs_ratio: float, curr_rs_ratio: float, curr_momentum: float
    ) -> bool:
        """Check if RS-Ratio crossed below 100 with negative momentum."""
        return prev_rs_ratio >= 100 and curr_rs_ratio < 100 and curr_momentum < 0

    @staticmethod
    def _create_quadrant_change_alert(
        ticker: str,
        sector: str,
        from_quad: str,
        to_quad: str,
        rs_ratio: float,
        rs_momentum: float,
    ) -> Optional[Dict[str, Any]]:
        """Create a quadrant change alert."""
        # Determine severity based on quadrant transitions
        severity = "info"

        # Critical transitions
        if from_quad == "Strengthening" and to_quad == "Weakening":
            severity = "critical"
            desc = f"{sector} ({ticker}) leadership fading: Strengthening → Weakening"
        elif from_quad == "Deteriorating" and to_quad == "Recovering":
            severity = "critical"
            desc = f"{sector} ({ticker}) rotation opportunity: Deteriorating → Recovering"
        # Other transitions are info-level
        else:
            desc = f"{sector} ({ticker}) rotated: {from_quad} → {to_quad}"

        return {
            "ticker": ticker,
            "sector": sector,
            "alert_type": "quadrant_change",
            "from_quadrant": from_quad,
            "to_quadrant": to_quad,
            "rs_ratio": rs_ratio,
            "rs_momentum": rs_momentum,
            "description": desc,
            "severity": severity,
        }

    @staticmethod
    def _create_momentum_reversal_alert(
        ticker: str,
        sector: str,
        rs_ratio: float,
        curr_momentum: float,
        prev_momentum: float,
    ) -> Dict[str, Any]:
        """Create a momentum reversal alert."""
        direction = "negative" if curr_momentum < 0 else "positive"
        return {
            "ticker": ticker,
            "sector": sector,
            "alert_type": "momentum_reversal",
            "from_quadrant": None,
            "to_quadrant": None,
            "rs_ratio": rs_ratio,
            "rs_momentum": curr_momentum,
            "description": f"{sector} ({ticker}) momentum reversed to {direction}",
            "severity": "warning",
        }

    @staticmethod
    def _create_breakout_alert(
        ticker: str, sector: str, rs_ratio: float, rs_momentum: float
    ) -> Dict[str, Any]:
        """Create a breakout alert (RS-Ratio crossing above 100)."""
        return {
            "ticker": ticker,
            "sector": sector,
            "alert_type": "breakout",
            "from_quadrant": None,
            "to_quadrant": None,
            "rs_ratio": rs_ratio,
            "rs_momentum": rs_momentum,
            "description": f"{sector} ({ticker}) breaking out: RS-Ratio crossed above 100",
            "severity": "warning",
        }

    @staticmethod
    def _create_breakdown_alert(
        ticker: str, sector: str, rs_ratio: float, rs_momentum: float
    ) -> Dict[str, Any]:
        """Create a breakdown alert (RS-Ratio crossing below 100)."""
        return {
            "ticker": ticker,
            "sector": sector,
            "alert_type": "breakdown",
            "from_quadrant": None,
            "to_quadrant": None,
            "rs_ratio": rs_ratio,
            "rs_momentum": rs_momentum,
            "description": f"{sector} ({ticker}) breaking down: RS-Ratio crossed below 100",
            "severity": "warning",
        }

    @staticmethod
    def enrich_alerts_with_systemic_context(
        alerts: List[Dict[str, Any]],
        regime_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enrich rotation alerts with systemic risk context from the regime detector.

        When AR delta z-score > 1.0, sectors rotating into Leading get a caution flag.
        When AR delta z-score < -1.0, sectors rotating into Improving get a confidence boost.
        When Windham state is fragile, ALL rotation alerts get a systemic warning.
        """
        if not regime_data:
            return alerts

        systemic = regime_data.get("systemic_risk", {})
        windham = regime_data.get("windham", {})
        ar_delta_zscore = systemic.get("absorption_delta_zscore") or systemic.get("ar_delta_zscore", 0.0)
        windham_state = windham.get("state", "resilient-calm")
        persistence = systemic.get("persistence") or systemic.get("windham_persistence", 0)

        enriched = []
        for alert in alerts:
            alert = dict(alert)  # copy to avoid mutation
            to_quad = alert.get("to_quadrant", "")

            if ar_delta_zscore > 1.0 and to_quad == "Leading":
                alert["systemic_warning"] = (
                    "Caution: absorption ratio rising — systemic coupling increasing. "
                    "Rotation into Leading may reverse if market fragility builds."
                )
                alert["systemic_flag"] = "caution"
            elif ar_delta_zscore < -1.0 and to_quad == "Improving":
                alert["systemic_boost"] = (
                    "Systemic decorrelation supports rotation thesis — "
                    "markets becoming more diversified."
                )
                alert["systemic_flag"] = "supportive"

            if windham_state in ("fragile-calm", "fragile-turbulent"):
                duration = f" ({persistence} consecutive periods)" if persistence and persistence > 1 else ""
                alert["systemic_regime_warning"] = (
                    f"Market in {windham.get('label', windham_state)}{duration}. "
                    f"Sector rotations may be unreliable during systemic fragility."
                )
                if windham_state == "fragile-turbulent":
                    alert["severity"] = "critical"

            enriched.append(alert)
        return enriched
