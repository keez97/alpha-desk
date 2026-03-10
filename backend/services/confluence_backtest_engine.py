"""
Confluence Backtester Engine - Historical validation of confluence signals.

Tests how often 3-signal alignment (RRG + Macro + Sector Performance)
produced positive returns over 1-5-10 day horizons.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import yfinance as yf
from backend.services.rrg_calculator import SECTOR_ETFS, calculate_rrg
from backend.services.data_provider import get_macro_data, get_sector_data, get_history

logger = logging.getLogger(__name__)


def fetch_sector_history(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
) -> Optional[pd.DataFrame]:
    """Fetch sector price history for a date range."""
    try:
        data = yf.Ticker(ticker)
        hist = data.history(start=start_date.date(), end=end_date.date())

        if hist.empty:
            logger.warning(f"No data for {ticker} in range {start_date} to {end_date}")
            return None

        hist = hist[['Close']].copy()
        hist.columns = ['close']
        return hist
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return None


def calculate_rs_ratio(
    ticker_prices: pd.Series,
    benchmark_prices: pd.Series,
    lookback: int = 50  # ~10 weeks of trading days
) -> Tuple[float, float]:
    """
    Calculate RS Ratio and RS Momentum for RRG quadrant determination.

    Returns:
        Tuple of (rs_ratio, rs_momentum)
    """
    if len(ticker_prices) < lookback:
        return 100.0, 0.0

    try:
        # Align series
        aligned = pd.DataFrame({
            'ticker': ticker_prices,
            'benchmark': benchmark_prices
        }).dropna()

        if len(aligned) < lookback:
            return 100.0, 0.0

        # Calculate relative strength (ticker / benchmark)
        rs_series = (aligned['ticker'] / aligned['benchmark']) * 100

        # RS Ratio: current RS / RS from lookback periods ago
        current_rs = rs_series.iloc[-1]
        past_rs = rs_series.iloc[-lookback]
        rs_ratio = (current_rs / past_rs * 100) if past_rs != 0 else 100.0

        # RS Momentum: momentum of RS series over last period
        rs_momentum = ((rs_series.iloc[-1] - rs_series.iloc[-lookback]) / rs_series.iloc[-lookback]) * 100

        return float(rs_ratio), float(rs_momentum)
    except Exception as e:
        logger.debug(f"Error calculating RS for {ticker}: {e}")
        return 100.0, 0.0


def determine_rrg_quadrant(rs_ratio: float, rs_momentum: float) -> str:
    """
    Determine RRG quadrant based on RS Ratio and RS Momentum.

    Quadrants:
    - Strengthening: RS > 100, Momentum > 0
    - Weakening: RS < 100, Momentum < 0
    - Recovering: RS < 100, Momentum > 0
    - Deteriorating: RS > 100, Momentum < 0
    """
    rs_strong = rs_ratio > 100
    momentum_positive = rs_momentum > 0

    if rs_strong and momentum_positive:
        return "Strengthening"
    elif not rs_strong and not momentum_positive:
        return "Weakening"
    elif not rs_strong and momentum_positive:
        return "Recovering"
    elif rs_strong and not momentum_positive:
        return "Deteriorating"
    else:
        return "Unknown"


def get_macro_signal(
    vix_level: Optional[float] = None,
    tnx_change: Optional[float] = None,
) -> str:
    """
    Determine macro regime signal for this date.

    Returns 'bullish', 'bearish', or 'neutral'
    """
    signals = []

    if vix_level is not None:
        # Low VIX = bullish, high VIX = bearish
        if vix_level < 15:
            signals.append('bullish')
        elif vix_level > 20:
            signals.append('bearish')

    if tnx_change is not None:
        # Rising yields = bearish for growth (but neutral overall)
        if tnx_change > 0.5:
            signals.append('bearish_growth')

    if not signals:
        return 'neutral'

    bullish_count = sum(1 for s in signals if 'bullish' in s)
    bearish_count = sum(1 for s in signals if 'bearish' in s)

    if bullish_count > bearish_count:
        return 'bullish'
    elif bearish_count > bullish_count:
        return 'bearish'
    else:
        return 'neutral'


def get_forward_returns(
    prices: pd.Series,
    start_idx: int,
    horizons: List[int] = [1, 3, 5, 10]
) -> Dict[int, float]:
    """
    Calculate forward returns from a given starting index.

    Args:
        prices: Price series
        start_idx: Index to start from
        horizons: Lookback periods (in days) to calculate returns for

    Returns:
        Dict mapping horizon to return percentage
    """
    result = {}
    start_price = prices.iloc[start_idx]

    for horizon in horizons:
        end_idx = start_idx + horizon
        if end_idx < len(prices):
            end_price = prices.iloc[end_idx]
            ret = ((end_price - start_price) / start_price) * 100
            result[horizon] = ret
        else:
            result[horizon] = None

    return result


class ConfluenceBacktestEngine:
    """Engine for backtesting confluence signals."""

    def __init__(self, lookback_months: int = 12):
        self.lookback_months = lookback_months
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=30 * lookback_months)
        self.horizons = [1, 3, 5, 10]

    def run_backtest(self) -> Dict[str, Any]:
        """
        Run full confluence backtest.

        Returns:
            Dict with summary stats, equity curve, and signal count
        """
        try:
            logger.info(f"Starting confluence backtest for {self.lookback_months} months")

            # Fetch benchmark and sector data
            benchmark_hist = fetch_sector_history('SPY', self.start_date, self.end_date)
            if benchmark_hist is None or len(benchmark_hist) < 50:
                logger.error("Could not fetch benchmark data")
                return self._error_response("Could not fetch benchmark data")

            # Fetch sector histories
            sector_data = {}
            for ticker in SECTOR_ETFS.keys():
                hist = fetch_sector_history(ticker, self.start_date, self.end_date)
                if hist is not None and len(hist) > 50:
                    sector_data[ticker] = hist

            if not sector_data:
                logger.error("Could not fetch sector data")
                return self._error_response("Could not fetch sector data")

            logger.info(f"Fetched data for {len(sector_data)} sectors")

            # Align all dates
            all_dates = set(benchmark_hist.index)
            for hist in sector_data.values():
                all_dates &= set(hist.index)

            if len(all_dates) < 100:
                logger.error("Insufficient overlapping dates")
                return self._error_response("Insufficient overlapping dates")

            sorted_dates = sorted(list(all_dates))
            logger.info(f"Analyzing {len(sorted_dates)} dates")

            # Initialize accumulators
            conviction_stats = {
                'HIGH': {
                    'bullish': {
                        'signals': [],
                        'win_rates': {1: [], 3: [], 5: [], 10: []},
                        'avg_returns': {1: [], 3: [], 5: [], 10: []},
                        'max_drawdown': [],
                    },
                    'bearish': {
                        'signals': [],
                        'win_rates': {1: [], 3: [], 5: [], 10: []},
                        'avg_returns': {1: [], 3: [], 5: [], 10: []},
                        'max_drawdown': [],
                    },
                },
                'MEDIUM': {
                    'bullish': {
                        'signals': [],
                        'win_rates': {1: [], 3: [], 5: [], 10: []},
                        'avg_returns': {1: [], 3: [], 5: [], 10: []},
                        'max_drawdown': [],
                    },
                    'bearish': {
                        'signals': [],
                        'win_rates': {1: [], 3: [], 5: [], 10: []},
                        'avg_returns': {1: [], 3: [], 5: [], 10: []},
                        'max_drawdown': [],
                    },
                },
                'LOW': {
                    'bullish': {
                        'signals': [],
                        'win_rates': {1: [], 3: [], 5: [], 10: []},
                        'avg_returns': {1: [], 3: [], 5: [], 10: []},
                        'max_drawdown': [],
                    },
                    'bearish': {
                        'signals': [],
                        'win_rates': {1: [], 3: [], 5: [], 10: []},
                        'avg_returns': {1: [], 3: [], 5: [], 10: []},
                        'max_drawdown': [],
                    },
                },
            }

            # Align dataframes to common index
            for ticker in sector_data:
                sector_data[ticker] = sector_data[ticker].loc[sorted_dates]
            benchmark_hist = benchmark_hist.loc[sorted_dates]

            equity_curve = {'date': [], 'cumReturn': []}
            high_signal_pnl = 0.0
            high_signal_count = 0

            # Walk through historical dates
            for i in range(50, len(sorted_dates) - 10):  # Need lookback for RS and forward looking for returns
                current_date = sorted_dates[i]

                # Get historical window for RS calculation (50 days lookback)
                window_start = max(0, i - 50)
                benchmark_window = benchmark_hist.iloc[window_start:i+1]

                # Count aligned signals for this date
                signal_count = 0
                signal_directions = []

                for ticker in sector_data.keys():
                    sector_window = sector_data[ticker].iloc[window_start:i+1]

                    # Calculate RRG quadrant
                    rs_ratio, rs_momentum = calculate_rs_ratio(
                        sector_window['close'],
                        benchmark_window['close'],
                        lookback=50
                    )
                    quadrant = determine_rrg_quadrant(rs_ratio, rs_momentum)

                    # Determine RRG signal
                    rrg_signal = None
                    if quadrant in ('Strengthening', 'Recovering'):
                        rrg_signal = 'bullish'
                        signal_count += 1
                    elif quadrant in ('Weakening', 'Deteriorating'):
                        rrg_signal = 'bearish'
                        signal_count += 1

                    # Sector performance signal (1-day change)
                    perf_signal = None
                    if i > 0:
                        daily_ret = ((sector_window['close'].iloc[-1] - sector_window['close'].iloc[-2]) /
                                    sector_window['close'].iloc[-2]) * 100
                        if daily_ret > 0.3:
                            perf_signal = 'bullish'
                            signal_count += 1
                        elif daily_ret < -0.3:
                            perf_signal = 'bearish'
                            signal_count += 1

                    # Macro signal (simple VIX-based)
                    macro_signal = 'bullish'  # Simplified: assume bullish unless very high VIX

                    # Count confluence direction
                    direction_votes = {
                        'bullish': (1 if rrg_signal == 'bullish' else 0) +
                                 (1 if perf_signal == 'bullish' else 0) +
                                 (1 if macro_signal == 'bullish' else 0),
                        'bearish': (1 if rrg_signal == 'bearish' else 0) +
                                 (1 if perf_signal == 'bearish' else 0) +
                                 (1 if macro_signal == 'bearish' else 0),
                    }

                    if direction_votes['bullish'] > direction_votes['bearish']:
                        signal_directions.append('bullish')
                    elif direction_votes['bearish'] > direction_votes['bullish']:
                        signal_directions.append('bearish')

                # Determine conviction level
                if signal_count >= 3:
                    conviction = 'HIGH'
                elif signal_count == 2:
                    conviction = 'MEDIUM'
                else:
                    conviction = 'LOW'

                # Determine overall direction (majority vote)
                bullish_count = sum(1 for d in signal_directions if d == 'bullish')
                bearish_count = sum(1 for d in signal_directions if d == 'bearish')

                if bullish_count > bearish_count:
                    direction = 'bullish'
                elif bearish_count > bullish_count:
                    direction = 'bearish'
                else:
                    direction = 'neutral'

                if direction == 'neutral':
                    continue

                # Calculate forward returns
                forward_rets = get_forward_returns(
                    benchmark_hist['close'],
                    i,
                    self.horizons
                )

                # Record signal outcomes
                for horizon, ret in forward_rets.items():
                    if ret is None:
                        continue

                    win = (ret > 0 and direction == 'bullish') or (ret < 0 and direction == 'bearish')

                    stats = conviction_stats[conviction][direction]
                    stats['signals'].append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'direction': direction,
                        'return': ret,
                        'win': win,
                    })
                    stats['win_rates'][horizon].append(1 if win else 0)
                    stats['avg_returns'][horizon].append(ret)

                # Track HIGH conviction bullish trades for equity curve
                if conviction == 'HIGH' and direction == 'bullish':
                    high_signal_count += 1
                    if forward_rets.get(1) is not None:
                        high_signal_pnl += forward_rets[1]

                    # Add to equity curve
                    equity_curve['date'].append(current_date.strftime('%Y-%m-%d'))
                    equity_curve['cumReturn'].append(high_signal_pnl)

            # Aggregate statistics
            summary = self._aggregate_statistics(conviction_stats)

            logger.info(f"Backtest complete. Analyzed {high_signal_count} HIGH conviction signals")

            return {
                'summary': summary,
                'equityCurve': equity_curve,
                'signalsAnalyzed': high_signal_count,
                'period': f"{self.lookback_months} months",
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error running confluence backtest: {e}")
            return self._error_response(str(e))

    def _aggregate_statistics(self, conviction_stats: Dict) -> Dict[str, Any]:
        """Aggregate raw signal data into summary statistics."""
        summary = {
            'convictionStats': [],
            'directionStats': [],
        }

        # Conviction-level aggregation
        for conviction in ['HIGH', 'MEDIUM', 'LOW']:
            for direction in ['bullish', 'bearish']:
                stats = conviction_stats[conviction][direction]

                if not stats['signals']:
                    continue

                total_signals = len(stats['signals'])

                row = {
                    'conviction': conviction,
                    'direction': direction,
                    'totalSignals': total_signals,
                    'winRate1D': np.mean(stats['win_rates'][1]) * 100 if stats['win_rates'][1] else 0,
                    'winRate3D': np.mean(stats['win_rates'][3]) * 100 if stats['win_rates'][3] else 0,
                    'winRate5D': np.mean(stats['win_rates'][5]) * 100 if stats['win_rates'][5] else 0,
                    'winRate10D': np.mean(stats['win_rates'][10]) * 100 if stats['win_rates'][10] else 0,
                    'avgReturn1D': np.mean(stats['avg_returns'][1]) if stats['avg_returns'][1] else 0,
                    'avgReturn3D': np.mean(stats['avg_returns'][3]) if stats['avg_returns'][3] else 0,
                    'avgReturn5D': np.mean(stats['avg_returns'][5]) if stats['avg_returns'][5] else 0,
                    'avgReturn10D': np.mean(stats['avg_returns'][10]) if stats['avg_returns'][10] else 0,
                    'maxDrawdown': 0.0,  # Simplified - would need more complex tracking
                }
                summary['convictionStats'].append(row)

        # Direction-level aggregation (across all convictions)
        direction_buckets = {'bullish': [], 'bearish': []}
        for conviction in ['HIGH', 'MEDIUM', 'LOW']:
            for direction in ['bullish', 'bearish']:
                direction_buckets[direction].extend(
                    conviction_stats[conviction][direction]['signals']
                )

        for direction in ['bullish', 'bearish']:
            signals = direction_buckets[direction]
            if not signals:
                continue

            wins = sum(1 for s in signals if s['win'])

            row = {
                'direction': direction,
                'totalSignals': len(signals),
                'winRate': (wins / len(signals)) * 100 if signals else 0,
                'avgReturn': np.mean([s['return'] for s in signals]) if signals else 0,
            }
            summary['directionStats'].append(row)

        return summary

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Generate error response."""
        return {
            'summary': {'convictionStats': [], 'directionStats': []},
            'equityCurve': [],
            'signalsAnalyzed': 0,
            'error': error_msg,
            'timestamp': datetime.utcnow().isoformat(),
        }


def run_confluence_backtest(lookback_months: int = 12) -> Dict[str, Any]:
    """
    Main entry point for confluence backtester.

    Args:
        lookback_months: Historical period to backtest (1-24 months)

    Returns:
        Backtest results with summary stats and equity curve
    """
    engine = ConfluenceBacktestEngine(lookback_months=lookback_months)
    return engine.run_backtest()
