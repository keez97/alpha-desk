"""
Intraday Momentum Engine - detects intraday breakout signals for sectors in leading quadrants.

Analyzes 5-min and 15-min candles to identify:
- Momentum: rate of change over last 3 bars
- Volume surge: current bar volume vs 20-bar average
- VWAP deviation: current price vs intraday VWAP
- Breakout signals: momentum > 0 AND volume surge > 1.5x AND price > VWAP

Only flags sectors in Strengthening or Leading (Recovering) RRG quadrants.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS

logger = logging.getLogger(__name__)


class IntradaySignal:
    """Represents an intraday momentum signal for a sector ETF."""

    def __init__(
        self,
        ticker: str,
        sector: str,
        interval: str,
        momentum: float,
        volume_surge: float,
        vwap_deviation: float,
        is_breakout: bool,
        price: float,
        timestamp: str,
    ):
        self.ticker = ticker
        self.sector = sector
        self.interval = interval
        self.momentum = momentum
        self.volume_surge = volume_surge
        self.vwap_deviation = vwap_deviation
        self.is_breakout = is_breakout
        self.price = price
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary."""
        return {
            "ticker": self.ticker,
            "sector": self.sector,
            "interval": self.interval,
            "momentum": self.momentum,
            "volumeSurge": self.volume_surge,
            "vwapDeviation": self.vwap_deviation,
            "isBreakout": self.is_breakout,
            "price": self.price,
            "timestamp": self.timestamp,
        }


class IntradayMomentumEngine:
    """Stateless engine for detecting intraday momentum breakouts in leading sectors."""

    # Only scan these quadrants (bullish positioning)
    LEADING_QUADRANTS = {"Strengthening", "Recovering"}

    @staticmethod
    def scan_intraday_momentum(
        interval: str = "5m", benchmark: str = "SPY", weeks: int = 10
    ) -> Dict[str, Any]:
        """
        Scan intraday momentum for sectors in leading RRG quadrants.

        Args:
            interval: "5m" or "15m" for intraday data
            benchmark: Benchmark ticker for RRG (default "SPY")
            weeks: Number of weeks for RRG calculation (default 10)

        Returns:
            Dict with keys: signals (List[IntradaySignal]), timestamp, sectors_scanned
        """
        try:
            # Get RRG data to identify leading sectors
            tickers = list(SECTOR_ETFS.keys())
            rrg_data = calculate_rrg(tickers, benchmark=benchmark, weeks=weeks)
            sectors = rrg_data.get("sectors", [])

            # Build lookup of leading sectors
            leading_sectors = {}
            for sector in sectors:
                ticker = sector.get("ticker")
                quadrant = sector.get("quadrant", "")
                if quadrant in IntradayMomentumEngine.LEADING_QUADRANTS:
                    leading_sectors[ticker] = sector

            # Scan intraday data for leading sectors
            signals = []
            scanned_count = 0

            for ticker in leading_sectors.keys():
                try:
                    signal = IntradayMomentumEngine._analyze_ticker(
                        ticker, interval, leading_sectors[ticker]
                    )
                    scanned_count += 1
                    if signal:
                        signals.append(signal)
                except Exception as e:
                    logger.error(f"Error analyzing intraday {ticker}: {e}")
                    continue

            return {
                "signals": [s.to_dict() for s in signals],
                "timestamp": datetime.utcnow().isoformat(),
                "sectors_scanned": scanned_count,
                "interval": interval,
                "benchmark": benchmark,
            }

        except Exception as e:
            logger.error(f"Error scanning intraday momentum: {e}")
            return {
                "signals": [],
                "timestamp": datetime.utcnow().isoformat(),
                "sectors_scanned": 0,
                "interval": interval,
                "error": str(e),
            }

    @staticmethod
    def _analyze_ticker(
        ticker: str, interval: str, sector_info: Dict[str, Any]
    ) -> Optional[IntradaySignal]:
        """
        Analyze single ticker for intraday momentum breakout.

        Args:
            ticker: Sector ETF ticker (e.g., "XLK")
            interval: "5m" or "15m"
            sector_info: RRG sector info with quadrant and name

        Returns:
            IntradaySignal if breakout detected, None otherwise
        """
        try:
            # Fetch intraday data
            intraday_df = IntradayMomentumEngine._fetch_intraday_data(
                ticker, interval
            )

            if intraday_df is None or len(intraday_df) < 3:
                logger.warning(f"Insufficient intraday data for {ticker}")
                return None

            # Calculate metrics
            momentum = IntradayMomentumEngine._calculate_momentum(intraday_df)
            volume_surge = IntradayMomentumEngine._calculate_volume_surge(
                intraday_df
            )
            vwap = IntradayMomentumEngine._calculate_vwap(intraday_df)
            current_price = intraday_df["Close"].iloc[-1]
            vwap_deviation = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0

            # Determine breakout: momentum > 0 AND volume surge > 1.5x AND price > VWAP
            is_breakout = (
                momentum > 0 and volume_surge > 1.5 and current_price > vwap
            )

            # Create signal
            signal = IntradaySignal(
                ticker=ticker,
                sector=sector_info.get("sector", ticker),
                interval=interval,
                momentum=momentum,
                volume_surge=volume_surge,
                vwap_deviation=vwap_deviation,
                is_breakout=is_breakout,
                price=float(current_price),
                timestamp=datetime.utcnow().isoformat(),
            )

            return signal

        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return None

    @staticmethod
    def _fetch_intraday_data(
        ticker: str, interval: str
    ) -> Optional[pd.DataFrame]:
        """
        Fetch intraday data from yfinance.

        Args:
            ticker: Stock/ETF ticker
            interval: "5m" or "15m"

        Returns:
            DataFrame with OHLCV or None on error
        """
        try:
            data = yf.download(
                ticker,
                period="1d",
                interval=interval,
                progress=False,
                prepost=False,
            )

            if data is None or data.empty:
                return None

            # Ensure columns are in expected format
            if isinstance(data.columns, pd.MultiIndex):
                # Multiple tickers (shouldn't happen with single ticker)
                data = data[ticker]

            # Standardize column names
            data.columns = [col.lower() for col in data.columns]

            return data
        except Exception as e:
            logger.error(f"Error fetching intraday data for {ticker}: {e}")
            return None

    @staticmethod
    def _calculate_momentum(df: pd.DataFrame) -> float:
        """
        Calculate momentum as rate of change over last 3 bars.

        Formula: (Close[0] - Close[-3]) / Close[-3] * 100

        Args:
            df: DataFrame with Close prices

        Returns:
            Momentum percentage (positive = bullish)
        """
        try:
            if len(df) < 3:
                return 0.0

            closes = df["close"].values
            current = closes[-1]
            three_bars_ago = closes[-3]

            if three_bars_ago == 0:
                return 0.0

            momentum = ((current - three_bars_ago) / three_bars_ago) * 100
            return float(momentum)
        except Exception as e:
            logger.error(f"Error calculating momentum: {e}")
            return 0.0

    @staticmethod
    def _calculate_volume_surge(df: pd.DataFrame) -> float:
        """
        Calculate volume surge as current bar volume vs 20-bar average.

        Args:
            df: DataFrame with Volume column

        Returns:
            Volume surge multiplier (e.g., 2.5 = 250% of average)
        """
        try:
            if len(df) < 1:
                return 0.0

            volumes = df["volume"].values
            current_volume = volumes[-1]

            # Use available bars if less than 20
            lookback = min(20, len(volumes) - 1) if len(volumes) > 1 else 1
            avg_volume = volumes[-lookback - 1 : -1].mean() if lookback > 0 else 1

            if avg_volume == 0:
                return 1.0

            surge = current_volume / avg_volume
            return float(surge)
        except Exception as e:
            logger.error(f"Error calculating volume surge: {e}")
            return 0.0

    @staticmethod
    def _calculate_vwap(df: pd.DataFrame) -> float:
        """
        Calculate intraday VWAP (Volume-Weighted Average Price).

        Formula: sum(Close * Volume) / sum(Volume)

        Args:
            df: DataFrame with Close and Volume

        Returns:
            VWAP value
        """
        try:
            if len(df) < 1:
                return 0.0

            closes = df["close"].values
            volumes = df["volume"].values

            # VWAP using cumulative calculation
            tp = (closes + closes + closes) / 3  # Typical Price = (H+L+C)/3, using C for simplicity
            vwap = (tp * volumes).sum() / volumes.sum()

            return float(vwap)
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return 0.0

    @staticmethod
    def get_ticker_detail(ticker: str, interval: str) -> Dict[str, Any]:
        """
        Get detailed intraday analysis for a specific sector ETF.

        Args:
            ticker: Sector ETF ticker
            interval: "5m" or "15m"

        Returns:
            Dict with detailed intraday metrics and last N candles
        """
        try:
            intraday_df = IntradayMomentumEngine._fetch_intraday_data(
                ticker, interval
            )

            if intraday_df is None or len(intraday_df) < 1:
                return {
                    "ticker": ticker,
                    "interval": interval,
                    "error": "No intraday data available",
                }

            # Calculate all metrics
            momentum = IntradayMomentumEngine._calculate_momentum(intraday_df)
            volume_surge = IntradayMomentumEngine._calculate_volume_surge(
                intraday_df
            )
            vwap = IntradayMomentumEngine._calculate_vwap(intraday_df)
            current_price = float(intraday_df["close"].iloc[-1])
            vwap_deviation = (
                ((current_price - vwap) / vwap * 100) if vwap > 0 else 0
            )

            # Build candle history (last 10 bars)
            candles = []
            for idx in range(max(0, len(intraday_df) - 10), len(intraday_df)):
                row = intraday_df.iloc[idx]
                candles.append(
                    {
                        "timestamp": str(intraday_df.index[idx]),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": int(row["volume"]),
                    }
                )

            return {
                "ticker": ticker,
                "interval": interval,
                "price": current_price,
                "momentum": momentum,
                "volumeSurge": volume_surge,
                "vwap": float(vwap),
                "vwapDeviation": vwap_deviation,
                "candles": candles,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting ticker detail for {ticker}: {e}")
            return {
                "ticker": ticker,
                "interval": interval,
                "error": str(e),
            }
