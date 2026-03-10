from backend.models.watchlist import Watchlist
from backend.models.portfolio import Portfolio, PortfolioHolding
from backend.models.report import WeeklyReport
from backend.models.cache import MorningBriefCache, StockGradeCache, ScreenerCache

# Factor Backtester models
from backend.models.securities import Security, SecurityLifecycleEvent
from backend.models.market_data import PriceHistory, FundamentalsSnapshot
from backend.models.factors import (
    FactorDefinition,
    FamaFrenchFactor,
    CustomFactorScore,
)
from backend.models.backtests import (
    Backtest,
    BacktestConfiguration,
    BacktestFactorAllocation,
    BacktestResult,
    BacktestStatistic,
    BacktestStatus,
    FactorCorrelation,
    AlphaDecayAnalysis,
    ScreenerFactorScore,
)

# Event Scanner models
from backend.models.events import (
    Event,
    EventClassificationRule,
    AlphaDecayWindow,
    EventFactorBridge,
    EventSourceMapping,
    EventAlertConfiguration,
    EventCorrelationAnalysis,
)

# Earnings Surprise Predictor models
from backend.models.earnings import (
    EarningsEstimate,
    EarningsActual,
    SmartEstimateWeights,
    AnalystScorecard,
    PEADMeasurement,
    EarningsSignal,
)

__all__ = [
    # Existing models
    "Watchlist",
    "Portfolio",
    "PortfolioHolding",
    "WeeklyReport",
    "MorningBriefCache",
    "StockGradeCache",
    "ScreenerCache",
    # Securities
    "Security",
    "SecurityLifecycleEvent",
    # Market Data
    "PriceHistory",
    "FundamentalsSnapshot",
    # Factors
    "FactorDefinition",
    "FamaFrenchFactor",
    "CustomFactorScore",
    # Backtests
    "Backtest",
    "BacktestConfiguration",
    "BacktestFactorAllocation",
    "BacktestResult",
    "BacktestStatistic",
    "BacktestStatus",
    "FactorCorrelation",
    "AlphaDecayAnalysis",
    "ScreenerFactorScore",
    # Event Scanner
    "Event",
    "EventClassificationRule",
    "AlphaDecayWindow",
    "EventFactorBridge",
    "EventSourceMapping",
    "EventAlertConfiguration",
    "EventCorrelationAnalysis",
    # Earnings Surprise Predictor
    "EarningsEstimate",
    "EarningsActual",
    "SmartEstimateWeights",
    "AnalystScorecard",
    "PEADMeasurement",
    "EarningsSignal",
]
