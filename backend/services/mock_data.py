"""
Comprehensive mock data for AlphaDesk demo and offline operation.
Contains realistic market data as of March 2026.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any

# Macro indicators with realistic March 2026 values
MOCK_MACRO_DATA = {
    "^TNX": {
        "price": 4.25,
        "change": 0.08,
        "pct_change": 1.92,
    },
    "^IRX": {
        "price": 4.65,
        "change": 0.10,
        "pct_change": 2.20,
    },
    "^VIX": {
        "price": 15.45,
        "change": -0.85,
        "pct_change": -5.21,
    },
    "DX-Y.NYB": {
        "price": 104.22,
        "change": 0.35,
        "pct_change": 0.34,
    },
    "GC=F": {
        "price": 2915.50,
        "change": 35.25,
        "pct_change": 1.23,
    },
    "CL=F": {
        "price": 67.45,
        "change": -1.55,
        "pct_change": -2.25,
    },
    "BTC-USD": {
        "price": 88450.75,
        "change": 3250.50,
        "pct_change": 3.81,
    },
    "SPY": {
        "price": 575.82,
        "change": 8.45,
        "pct_change": 1.49,
    },
    "QQQ": {
        "price": 490.35,
        "change": 12.15,
        "pct_change": 2.54,
    },
    "IWM": {
        "price": 210.45,
        "change": 3.22,
        "pct_change": 1.55,
    },
}

# All 11 sector ETFs with realistic prices and normalized chart data
MOCK_SECTOR_DATA = [
    {
        "ticker": "XLK",
        "sector": "Information Technology",
        "price": 203.45,
        "daily_change": 4.25,
        "daily_pct_change": 2.13,
        "chart_data": [100.0, 100.8, 101.2, 101.9, 102.1, 102.8, 103.5, 103.2, 104.1, 104.9, 105.2, 105.8, 106.1, 106.5, 107.2, 107.8, 108.3, 108.9, 109.2, 109.8],
    },
    {
        "ticker": "XLV",
        "sector": "Healthcare",
        "price": 157.82,
        "daily_change": 1.45,
        "daily_pct_change": 0.93,
        "chart_data": [100.0, 100.3, 100.8, 101.1, 101.4, 101.7, 102.0, 102.3, 102.5, 102.8, 103.1, 103.4, 103.7, 104.0, 104.3, 104.6, 104.9, 105.2, 105.5, 105.8],
    },
    {
        "ticker": "XLF",
        "sector": "Financials",
        "price": 182.35,
        "daily_change": 2.80,
        "daily_pct_change": 1.56,
        "chart_data": [100.0, 100.5, 101.0, 101.3, 101.8, 102.2, 102.6, 102.9, 103.3, 103.7, 104.1, 104.4, 104.8, 105.2, 105.6, 106.0, 106.4, 106.8, 107.2, 107.6],
    },
    {
        "ticker": "XLY",
        "sector": "Consumer Discretionary",
        "price": 196.45,
        "daily_change": 3.15,
        "daily_pct_change": 1.63,
        "chart_data": [100.0, 100.4, 100.9, 101.2, 101.7, 102.1, 102.6, 103.0, 103.5, 104.0, 104.4, 104.9, 105.4, 105.8, 106.3, 106.8, 107.2, 107.7, 108.1, 108.6],
    },
    {
        "ticker": "XLP",
        "sector": "Consumer Staples",
        "price": 168.92,
        "daily_change": 0.82,
        "daily_pct_change": 0.49,
        "chart_data": [100.0, 100.2, 100.5, 100.8, 101.1, 101.4, 101.7, 102.0, 102.3, 102.6, 102.9, 103.2, 103.5, 103.8, 104.1, 104.4, 104.7, 105.0, 105.3, 105.6],
    },
    {
        "ticker": "XLE",
        "sector": "Energy",
        "price": 142.15,
        "daily_change": -2.35,
        "daily_pct_change": -1.63,
        "chart_data": [100.0, 100.1, 99.8, 99.5, 99.2, 98.9, 98.6, 98.3, 98.0, 97.7, 97.4, 97.1, 96.8, 96.5, 96.2, 95.9, 95.6, 95.3, 95.0, 94.7],
    },
    {
        "ticker": "XLRE",
        "sector": "Real Estate",
        "price": 134.62,
        "daily_change": 1.15,
        "daily_pct_change": 0.86,
        "chart_data": [100.0, 100.3, 100.5, 100.8, 101.0, 101.3, 101.5, 101.8, 102.0, 102.3, 102.5, 102.8, 103.0, 103.3, 103.5, 103.8, 104.0, 104.3, 104.5, 104.8],
    },
    {
        "ticker": "XLI",
        "sector": "Industrials",
        "price": 191.28,
        "daily_change": 3.45,
        "daily_pct_change": 1.83,
        "chart_data": [100.0, 100.6, 101.1, 101.5, 102.0, 102.5, 103.0, 103.5, 104.0, 104.5, 105.0, 105.5, 106.0, 106.5, 107.0, 107.5, 108.0, 108.5, 109.0, 109.5],
    },
    {
        "ticker": "XLU",
        "sector": "Utilities",
        "price": 156.78,
        "daily_change": 0.45,
        "daily_pct_change": 0.29,
        "chart_data": [100.0, 100.1, 100.3, 100.5, 100.7, 100.9, 101.1, 101.3, 101.5, 101.7, 101.9, 102.1, 102.3, 102.5, 102.7, 102.9, 103.1, 103.3, 103.5, 103.7],
    },
    {
        "ticker": "XLC",
        "sector": "Communication Services",
        "price": 179.12,
        "daily_change": 2.68,
        "daily_pct_change": 1.52,
        "chart_data": [100.0, 100.5, 101.0, 101.4, 101.9, 102.4, 102.9, 103.3, 103.8, 104.3, 104.8, 105.2, 105.7, 106.2, 106.7, 107.1, 107.6, 108.1, 108.6, 109.1],
    },
]

# Market drivers with realistic headlines for March 2026
MOCK_MORNING_DRIVERS = {
    "drivers": [
        {
            "title": "Fed Signals Cautious Approach to Rate Cuts",
            "explanation": "Federal Reserve officials expressed measured optimism about inflation progress but emphasized the need for data-dependent decisions on future rate adjustments. Markets interpreted this as a potential pause in the hiking cycle.",
            "impact_score": 8.5,
            "sentiment": "neutral",
            "source": "Bloomberg",
            "url": "https://www.bloomberg.com/news/articles",
        },
        {
            "title": "Tech Earnings Exceed Expectations in Q1",
            "explanation": "Major semiconductor and software companies reported better-than-expected earnings, driven by continued AI infrastructure demand and cloud computing growth. This boosted technology sector sentiment.",
            "impact_score": 9.2,
            "sentiment": "bullish",
            "source": "Reuters",
            "url": "https://www.reuters.com/technology",
        },
        {
            "title": "Oil Falls on Demand Concerns Amid Economic Slowdown Fears",
            "explanation": "Crude oil prices declined as investors expressed concerns about global demand in light of mixed economic indicators. OPEC is monitoring the situation closely.",
            "impact_score": 7.8,
            "sentiment": "bearish",
            "source": "CNBC",
            "url": "https://www.cnbc.com/energy",
        },
        {
            "title": "Dollar Strengthens Against Major Currencies",
            "explanation": "The US Dollar Index rose to a three-week high as investors sought safe-haven assets. This reflects persistent geopolitical uncertainties and mixed global growth signals.",
            "impact_score": 7.2,
            "sentiment": "neutral",
            "source": "Financial Times",
            "url": "https://www.ft.com/markets",
        },
        {
            "title": "AI Stock Rally Continues with Positive Guidance Updates",
            "explanation": "Multiple AI-focused companies issued optimistic forward guidance, citing strong enterprise demand and expanding use cases. This pushed AI-adjacent stocks to new highs.",
            "impact_score": 9.0,
            "sentiment": "bullish",
            "source": "MarketWatch",
            "url": "https://www.marketwatch.com/investing",
        },
    ]
}

# Stock grades for example holdings
MOCK_STOCK_GRADES = {
    "AAPL": {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "grade": "BUY",
        "overall_score": 8.2,
        "metrics": {
            "valuation": {
                "grade": "A",
                "score": 8.5,
                "reason": "Trading at reasonable 24.5x forward earnings with strong cash generation",
            },
            "growth": {
                "grade": "A",
                "score": 8.8,
                "reason": "Services segment growing 12% YoY, installed base expanding globally",
            },
            "quality": {
                "grade": "A",
                "score": 8.9,
                "reason": "Consistent profitability, strong margins, industry-leading ecosystem",
            },
            "momentum": {
                "grade": "B+",
                "score": 7.8,
                "reason": "Positive price momentum with above-average volume on rallies",
            },
            "technicals": {
                "grade": "B",
                "score": 7.5,
                "reason": "Above 50-day MA, RSI at 65, some profit-taking near resistance",
            },
        },
        "recommendation": "Strong buy for growth and quality investors",
    },
    "MSFT": {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "grade": "BUY",
        "overall_score": 8.5,
        "metrics": {
            "valuation": {
                "grade": "A",
                "score": 8.7,
                "reason": "Cloud business justifies 28x forward PE with 30%+ growth rates",
            },
            "growth": {
                "grade": "A+",
                "score": 9.1,
                "reason": "Azure growing 29% YoY, OpenAI partnership driving innovation",
            },
            "quality": {
                "grade": "A",
                "score": 8.9,
                "reason": "Recession-resistant business model, strong competitive moat",
            },
            "momentum": {
                "grade": "A",
                "score": 8.6,
                "reason": "Breaking above 200-day MA, institutional buying strong",
            },
            "technicals": {
                "grade": "A",
                "score": 8.4,
                "reason": "Healthy breakout pattern, volume confirming uptrend",
            },
        },
        "recommendation": "Excellent buy for growth portfolios with multi-year hold horizon",
    },
    "NVDA": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "grade": "HOLD",
        "overall_score": 7.6,
        "metrics": {
            "valuation": {
                "grade": "B",
                "score": 7.2,
                "reason": "Premium valuation at 45x forward earnings, priced for continued perfection",
            },
            "growth": {
                "grade": "A",
                "score": 8.8,
                "reason": "AI chip demand remains strong, data center revenue robust",
            },
            "quality": {
                "grade": "A",
                "score": 8.7,
                "reason": "Market leader in AI chips, strong moat from software ecosystem",
            },
            "momentum": {
                "grade": "B+",
                "score": 7.8,
                "reason": "Strong uptrend but near overbought, some volatility expected",
            },
            "technicals": {
                "grade": "B",
                "score": 7.1,
                "reason": "RSI near 75, potential pullback risk, watch support levels",
            },
        },
        "recommendation": "Hold for existing positions, wait for better entry points for new exposure",
    },
}

# Stock screener results
MOCK_SCREENER_RESULTS = {
    "date": "2026-03-07",
    "value_opportunities": [
        {
            "ticker": "JPM",
            "name": "JPMorgan Chase",
            "price": 185.45,
            "pe_ratio": 12.5,
            "pb_ratio": 1.15,
            "dividend_yield": 2.65,
            "pct_change_1m": 5.2,
            "score": 8.1,
        },
        {
            "ticker": "UNH",
            "name": "UnitedHealth Group",
            "price": 542.30,
            "pe_ratio": 18.2,
            "pb_ratio": 4.85,
            "dividend_yield": 1.12,
            "pct_change_1m": 3.8,
            "score": 7.8,
        },
        {
            "ticker": "TSM",
            "name": "Taiwan Semiconductor Manufacturing",
            "price": 195.75,
            "pe_ratio": 21.3,
            "pb_ratio": 3.45,
            "dividend_yield": 1.85,
            "pct_change_1m": 8.5,
            "score": 7.5,
        },
        {
            "ticker": "VOD",
            "name": "Vodafone Group",
            "price": 42.15,
            "pe_ratio": 8.9,
            "pb_ratio": 0.85,
            "dividend_yield": 5.45,
            "pct_change_1m": 1.2,
            "score": 7.2,
        },
        {
            "ticker": "BTI",
            "name": "British American Tobacco",
            "price": 31.85,
            "pe_ratio": 9.2,
            "pb_ratio": 2.15,
            "dividend_yield": 8.35,
            "pct_change_1m": 2.3,
            "score": 7.0,
        },
    ],
    "momentum_leaders": [
        {
            "ticker": "NVDA",
            "name": "NVIDIA",
            "price": 895.45,
            "pe_ratio": 45.2,
            "rs_momentum": 85,
            "pct_change_3m": 32.5,
            "score": 8.8,
        },
        {
            "ticker": "MSFT",
            "name": "Microsoft",
            "price": 425.80,
            "pe_ratio": 28.1,
            "rs_momentum": 78,
            "pct_change_3m": 24.3,
            "score": 8.5,
        },
        {
            "ticker": "AXON",
            "name": "Axon Enterprise",
            "price": 485.20,
            "pe_ratio": 35.6,
            "rs_momentum": 82,
            "pct_change_3m": 28.9,
            "score": 8.3,
        },
        {
            "ticker": "UPST",
            "name": "Upstart Holdings",
            "price": 78.45,
            "pe_ratio": 24.5,
            "rs_momentum": 75,
            "pct_change_3m": 19.8,
            "score": 7.9,
        },
        {
            "ticker": "MARA",
            "name": "Marathon Digital Holdings",
            "price": 31.55,
            "pe_ratio": 18.2,
            "rs_momentum": 72,
            "pct_change_3m": 18.2,
            "score": 7.6,
        },
    ],
}

# Weekly report structure matching the API schema
MOCK_WEEKLY_REPORT = {
    "week": "2026-03-03 to 2026-03-07",
    "summary": "Markets showed resilience this week as tech stocks continued their rally on strong AI-related earnings and positive guidance. The S&P 500 gained 1.49% to 575.82, while the Nasdaq-100 rose 2.54% to 490.35. Bond yields ticked higher as investors digested better-than-expected economic data. Sectors like Technology, Industrials, and Consumer Discretionary led gains.",
    "market_overview": {
        "indices": [
            {
                "ticker": "SPY",
                "name": "S&P 500",
                "price": 575.82,
                "week_change": 8.45,
                "week_pct_change": 1.49,
            },
            {
                "ticker": "QQQ",
                "name": "Nasdaq-100",
                "price": 490.35,
                "week_change": 12.15,
                "week_pct_change": 2.54,
            },
            {
                "ticker": "IWM",
                "name": "Russell 2000",
                "price": 210.45,
                "week_change": 3.22,
                "week_pct_change": 1.55,
            },
        ],
        "macro_indicators": {
            "ten_year_yield": 4.25,
            "vix": 15.45,
            "dxy": 104.22,
        },
    },
    "sector_analysis": {
        "best_performers": [
            {"sector": "Information Technology", "change": 2.13},
            {"sector": "Industrials", "change": 1.83},
            {"sector": "Consumer Discretionary", "change": 1.63},
        ],
        "worst_performers": [
            {"sector": "Energy", "change": -1.63},
            {"sector": "Utilities", "change": 0.29},
            {"sector": "Consumer Staples", "change": 0.49},
        ],
    },
    "key_drivers": [
        {
            "headline": "Tech Earnings Beat Expectations on AI Demand",
            "impact": "Positive",
            "details": "Multiple semiconductor and software companies reported better-than-expected results",
        },
        {
            "headline": "Fed Signals Measured Approach to Future Rate Decisions",
            "impact": "Neutral",
            "details": "Powell stated data dependency while acknowledging inflation progress",
        },
        {
            "headline": "Oil Declines on Demand Concerns",
            "impact": "Negative",
            "details": "WTI crude fell 2.25% amid economic slowdown worries",
        },
    ],
    "portfolio_analysis": {
        "top_holdings": [
            {
                "ticker": "MSFT",
                "name": "Microsoft",
                "price": 425.80,
                "week_change": 3.45,
                "recommendation": "BUY",
                "grade": "A",
            },
            {
                "ticker": "NVDA",
                "name": "NVIDIA",
                "price": 895.45,
                "week_change": 28.50,
                "recommendation": "HOLD",
                "grade": "B",
            },
            {
                "ticker": "AAPL",
                "name": "Apple",
                "price": 198.50,
                "week_change": 2.15,
                "recommendation": "BUY",
                "grade": "A",
            },
        ],
        "allocation": {
            "technology": 35,
            "healthcare": 18,
            "financials": 15,
            "industrials": 12,
            "discretionary": 10,
            "other": 10,
        },
    },
    "outlook_and_recommendations": {
        "near_term_view": "Bullish",
        "confidence_level": 7.5,
        "key_levels": {
            "spy_resistance": 580,
            "spy_support": 565,
            "qqq_resistance": 500,
            "qqq_support": 480,
        },
        "watchlist": [
            "Monitor Fed communications for rate guidance",
            "Watch for earnings revisions in non-tech sectors",
            "Track oil prices for inflation implications",
            "Observe tech valuations for pullback opportunities",
        ],
    },
}

# Quote data for common tickers
MOCK_QUOTE_DATA = {
    "AAPL": {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "price": 198.50,
        "change": 2.15,
        "pct_change": 1.10,
        "volume": 48250000,
        "52w_high": 215.35,
        "52w_low": 165.80,
        "market_cap": 3100000000000,
        "sector": "Technology",
    },
    "MSFT": {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "price": 425.80,
        "change": 3.45,
        "pct_change": 0.82,
        "volume": 22150000,
        "52w_high": 445.25,
        "52w_low": 355.40,
        "market_cap": 3150000000000,
        "sector": "Technology",
    },
    "NVDA": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "price": 895.45,
        "change": 28.50,
        "pct_change": 3.29,
        "volume": 32450000,
        "52w_high": 950.20,
        "52w_low": 685.50,
        "market_cap": 2200000000000,
        "sector": "Technology",
    },
    "GOOG": {
        "ticker": "GOOG",
        "name": "Alphabet Inc.",
        "price": 156.75,
        "change": 1.85,
        "pct_change": 1.19,
        "volume": 25680000,
        "52w_high": 175.85,
        "52w_low": 128.95,
        "market_cap": 1950000000000,
        "sector": "Technology",
    },
    "AMZN": {
        "ticker": "AMZN",
        "name": "Amazon.com Inc.",
        "price": 215.30,
        "change": 2.80,
        "pct_change": 1.32,
        "volume": 42350000,
        "52w_high": 235.50,
        "52w_low": 155.33,
        "market_cap": 2250000000000,
        "sector": "Consumer Discretionary",
    },
    "META": {
        "ticker": "META",
        "name": "Meta Platforms Inc.",
        "price": 542.15,
        "change": 12.45,
        "pct_change": 2.35,
        "volume": 15680000,
        "52w_high": 575.40,
        "52w_low": 245.25,
        "market_cap": 1650000000000,
        "sector": "Technology",
    },
    "TSLA": {
        "ticker": "TSLA",
        "name": "Tesla Inc.",
        "price": 285.60,
        "change": -3.25,
        "pct_change": -1.13,
        "volume": 125680000,
        "52w_high": 320.50,
        "52w_low": 155.35,
        "market_cap": 920000000000,
        "sector": "Consumer Discretionary",
    },
    "JPM": {
        "ticker": "JPM",
        "name": "JPMorgan Chase & Co.",
        "price": 185.45,
        "change": 1.25,
        "pct_change": 0.68,
        "volume": 8950000,
        "52w_high": 205.75,
        "52w_low": 155.20,
        "market_cap": 520000000000,
        "sector": "Financials",
    },
    "V": {
        "ticker": "V",
        "name": "Visa Inc.",
        "price": 285.75,
        "change": 2.15,
        "pct_change": 0.76,
        "volume": 5685000,
        "52w_high": 310.50,
        "52w_low": 235.80,
        "market_cap": 610000000000,
        "sector": "Financials",
    },
    "UNH": {
        "ticker": "UNH",
        "name": "UnitedHealth Group Inc.",
        "price": 542.30,
        "change": 3.80,
        "pct_change": 0.70,
        "volume": 2450000,
        "52w_high": 580.50,
        "52w_low": 420.85,
        "market_cap": 525000000000,
        "sector": "Healthcare",
    },
}

# Ticker search results for common queries
MOCK_SEARCH_RESULTS = {
    "apple": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
        }
    ],
    "microsoft": [
        {
            "ticker": "MSFT",
            "name": "Microsoft Corporation",
            "sector": "Technology",
        }
    ],
    "nvidia": [
        {
            "ticker": "NVDA",
            "name": "NVIDIA Corporation",
            "sector": "Technology",
        }
    ],
    "google": [
        {
            "ticker": "GOOG",
            "name": "Alphabet Inc.",
            "sector": "Technology",
        },
        {
            "ticker": "GOOGL",
            "name": "Alphabet Inc.",
            "sector": "Technology",
        },
    ],
    "amazon": [
        {
            "ticker": "AMZN",
            "name": "Amazon.com Inc.",
            "sector": "Consumer Discretionary",
        }
    ],
    "meta": [
        {
            "ticker": "META",
            "name": "Meta Platforms Inc.",
            "sector": "Technology",
        }
    ],
    "tesla": [
        {
            "ticker": "TSLA",
            "name": "Tesla Inc.",
            "sector": "Consumer Discretionary",
        }
    ],
    "jpmorgan": [
        {
            "ticker": "JPM",
            "name": "JPMorgan Chase & Co.",
            "sector": "Financials",
        }
    ],
    "visa": [
        {
            "ticker": "V",
            "name": "Visa Inc.",
            "sector": "Financials",
        }
    ],
    "unitedhealth": [
        {
            "ticker": "UNH",
            "name": "UnitedHealth Group Inc.",
            "sector": "Healthcare",
        }
    ],
}

# Fundamental data for stock grading
MOCK_FUNDAMENTALS = {
    "AAPL": {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 3100000000000,
        "pe_ratio": 24.5,
        "peg_ratio": 2.1,
        "forward_pe": 23.8,
        "price_to_book": 82.5,
        "price_to_sales": 28.3,
        "debt_to_equity": 1.85,
        "current_ratio": 1.12,
        "quick_ratio": 1.08,
        "beta": 1.21,
        "dividend_yield": 0.42,
        "payout_ratio": 0.22,
        "short_interest": 0.018,
        "institutional_ownership": 0.61,
        "insider_ownership": 0.004,
        "eps": 8.10,
        "eps_growth": 0.085,
        "revenue": 391035000000,
        "net_income": 93736000000,
        "operating_cash_flow": 110543000000,
        "free_cash_flow": 95467000000,
        "52w_high": 215.35,
        "52w_low": 165.80,
        "50day_ma": 195.20,
        "200day_ma": 188.50,
    },
    "MSFT": {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "industry": "Software",
        "market_cap": 3150000000000,
        "pe_ratio": 28.1,
        "peg_ratio": 2.3,
        "forward_pe": 26.5,
        "price_to_book": 12.5,
        "price_to_sales": 13.2,
        "debt_to_equity": 0.58,
        "current_ratio": 1.95,
        "quick_ratio": 1.91,
        "beta": 0.95,
        "dividend_yield": 0.72,
        "payout_ratio": 0.28,
        "short_interest": 0.012,
        "institutional_ownership": 0.73,
        "insider_ownership": 0.002,
        "eps": 15.15,
        "eps_growth": 0.095,
        "revenue": 245122000000,
        "net_income": 88158000000,
        "operating_cash_flow": 89456000000,
        "free_cash_flow": 81234000000,
        "52w_high": 445.25,
        "52w_low": 355.40,
        "50day_ma": 420.50,
        "200day_ma": 405.75,
    },
    "NVDA": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "sector": "Technology",
        "industry": "Semiconductors",
        "market_cap": 2200000000000,
        "pe_ratio": 45.2,
        "peg_ratio": 1.8,
        "forward_pe": 35.8,
        "price_to_book": 35.5,
        "price_to_sales": 22.1,
        "debt_to_equity": 0.38,
        "current_ratio": 3.45,
        "quick_ratio": 3.21,
        "beta": 1.75,
        "dividend_yield": 0.01,
        "payout_ratio": 0.01,
        "short_interest": 0.025,
        "institutional_ownership": 0.64,
        "insider_ownership": 0.008,
        "eps": 19.81,
        "eps_growth": 0.42,
        "revenue": 126522000000,
        "net_income": 48050000000,
        "operating_cash_flow": 52125000000,
        "free_cash_flow": 48932000000,
        "52w_high": 950.20,
        "52w_low": 685.50,
        "50day_ma": 880.35,
        "200day_ma": 825.60,
    },
}

# RRG (Relative Rotation Graph) data for sectors
MOCK_RRG_DATA = [
    {
        "ticker": "XLK",
        "sector": "Information Technology",
        "trail": [
            {"week": 0, "rs_ratio": 1.02, "rs_momentum": 5.2},
            {"week": 1, "rs_ratio": 1.03, "rs_momentum": 5.8},
            {"week": 2, "rs_ratio": 1.04, "rs_momentum": 6.5},
            {"week": 3, "rs_ratio": 1.05, "rs_momentum": 7.2},
            {"week": 4, "rs_ratio": 1.06, "rs_momentum": 8.1},
            {"week": 5, "rs_ratio": 1.07, "rs_momentum": 8.9},
            {"week": 6, "rs_ratio": 1.08, "rs_momentum": 9.5},
            {"week": 7, "rs_ratio": 1.09, "rs_momentum": 10.2},
            {"week": 8, "rs_ratio": 1.10, "rs_momentum": 10.8},
            {"week": 9, "rs_ratio": 1.11, "rs_momentum": 11.5},
        ],
    },
    {
        "ticker": "XLV",
        "sector": "Healthcare",
        "trail": [
            {"week": 0, "rs_ratio": 0.98, "rs_momentum": -2.1},
            {"week": 1, "rs_ratio": 0.99, "rs_momentum": -1.5},
            {"week": 2, "rs_ratio": 0.99, "rs_momentum": -0.8},
            {"week": 3, "rs_ratio": 1.00, "rs_momentum": 0.2},
            {"week": 4, "rs_ratio": 1.00, "rs_momentum": 0.9},
            {"week": 5, "rs_ratio": 1.01, "rs_momentum": 1.5},
            {"week": 6, "rs_ratio": 1.01, "rs_momentum": 2.2},
            {"week": 7, "rs_ratio": 1.02, "rs_momentum": 2.8},
            {"week": 8, "rs_ratio": 1.02, "rs_momentum": 3.2},
            {"week": 9, "rs_ratio": 1.03, "rs_momentum": 3.8},
        ],
    },
    {
        "ticker": "XLF",
        "sector": "Financials",
        "trail": [
            {"week": 0, "rs_ratio": 1.01, "rs_momentum": 2.5},
            {"week": 1, "rs_ratio": 1.02, "rs_momentum": 3.2},
            {"week": 2, "rs_ratio": 1.02, "rs_momentum": 3.8},
            {"week": 3, "rs_ratio": 1.03, "rs_momentum": 4.5},
            {"week": 4, "rs_ratio": 1.04, "rs_momentum": 5.2},
            {"week": 5, "rs_ratio": 1.04, "rs_momentum": 5.8},
            {"week": 6, "rs_ratio": 1.05, "rs_momentum": 6.3},
            {"week": 7, "rs_ratio": 1.05, "rs_momentum": 6.9},
            {"week": 8, "rs_ratio": 1.06, "rs_momentum": 7.4},
            {"week": 9, "rs_ratio": 1.07, "rs_momentum": 7.9},
        ],
    },
    {
        "ticker": "XLY",
        "sector": "Consumer Discretionary",
        "trail": [
            {"week": 0, "rs_ratio": 1.00, "rs_momentum": 1.2},
            {"week": 1, "rs_ratio": 1.01, "rs_momentum": 1.9},
            {"week": 2, "rs_ratio": 1.01, "rs_momentum": 2.6},
            {"week": 3, "rs_ratio": 1.02, "rs_momentum": 3.3},
            {"week": 4, "rs_ratio": 1.02, "rs_momentum": 4.0},
            {"week": 5, "rs_ratio": 1.03, "rs_momentum": 4.7},
            {"week": 6, "rs_ratio": 1.03, "rs_momentum": 5.3},
            {"week": 7, "rs_ratio": 1.04, "rs_momentum": 5.9},
            {"week": 8, "rs_ratio": 1.04, "rs_momentum": 6.5},
            {"week": 9, "rs_ratio": 1.05, "rs_momentum": 7.1},
        ],
    },
    {
        "ticker": "XLP",
        "sector": "Consumer Staples",
        "trail": [
            {"week": 0, "rs_ratio": 0.97, "rs_momentum": -3.2},
            {"week": 1, "rs_ratio": 0.97, "rs_momentum": -2.8},
            {"week": 2, "rs_ratio": 0.98, "rs_momentum": -2.3},
            {"week": 3, "rs_ratio": 0.98, "rs_momentum": -1.8},
            {"week": 4, "rs_ratio": 0.99, "rs_momentum": -1.2},
            {"week": 5, "rs_ratio": 0.99, "rs_momentum": -0.6},
            {"week": 6, "rs_ratio": 1.00, "rs_momentum": 0.1},
            {"week": 7, "rs_ratio": 1.00, "rs_momentum": 0.7},
            {"week": 8, "rs_ratio": 1.01, "rs_momentum": 1.3},
            {"week": 9, "rs_ratio": 1.01, "rs_momentum": 1.9},
        ],
    },
    {
        "ticker": "XLE",
        "sector": "Energy",
        "trail": [
            {"week": 0, "rs_ratio": 0.94, "rs_momentum": -8.5},
            {"week": 1, "rs_ratio": 0.93, "rs_momentum": -8.9},
            {"week": 2, "rs_ratio": 0.92, "rs_momentum": -9.2},
            {"week": 3, "rs_ratio": 0.91, "rs_momentum": -9.4},
            {"week": 4, "rs_ratio": 0.90, "rs_momentum": -9.6},
            {"week": 5, "rs_ratio": 0.89, "rs_momentum": -9.7},
            {"week": 6, "rs_ratio": 0.88, "rs_momentum": -9.8},
            {"week": 7, "rs_ratio": 0.87, "rs_momentum": -9.8},
            {"week": 8, "rs_ratio": 0.87, "rs_momentum": -9.7},
            {"week": 9, "rs_ratio": 0.86, "rs_momentum": -9.5},
        ],
    },
    {
        "ticker": "XLRE",
        "sector": "Real Estate",
        "trail": [
            {"week": 0, "rs_ratio": 0.99, "rs_momentum": -1.8},
            {"week": 1, "rs_ratio": 0.99, "rs_momentum": -1.3},
            {"week": 2, "rs_ratio": 1.00, "rs_momentum": -0.8},
            {"week": 3, "rs_ratio": 1.00, "rs_momentum": -0.2},
            {"week": 4, "rs_ratio": 1.01, "rs_momentum": 0.4},
            {"week": 5, "rs_ratio": 1.01, "rs_momentum": 1.0},
            {"week": 6, "rs_ratio": 1.02, "rs_momentum": 1.6},
            {"week": 7, "rs_ratio": 1.02, "rs_momentum": 2.2},
            {"week": 8, "rs_ratio": 1.03, "rs_momentum": 2.7},
            {"week": 9, "rs_ratio": 1.03, "rs_momentum": 3.2},
        ],
    },
    {
        "ticker": "XLI",
        "sector": "Industrials",
        "trail": [
            {"week": 0, "rs_ratio": 1.01, "rs_momentum": 3.5},
            {"week": 1, "rs_ratio": 1.02, "rs_momentum": 4.2},
            {"week": 2, "rs_ratio": 1.03, "rs_momentum": 4.9},
            {"week": 3, "rs_ratio": 1.04, "rs_momentum": 5.6},
            {"week": 4, "rs_ratio": 1.05, "rs_momentum": 6.3},
            {"week": 5, "rs_ratio": 1.06, "rs_momentum": 7.0},
            {"week": 6, "rs_ratio": 1.07, "rs_momentum": 7.6},
            {"week": 7, "rs_ratio": 1.08, "rs_momentum": 8.2},
            {"week": 8, "rs_ratio": 1.09, "rs_momentum": 8.7},
            {"week": 9, "rs_ratio": 1.10, "rs_momentum": 9.2},
        ],
    },
    {
        "ticker": "XLU",
        "sector": "Utilities",
        "trail": [
            {"week": 0, "rs_ratio": 0.96, "rs_momentum": -4.1},
            {"week": 1, "rs_ratio": 0.96, "rs_momentum": -3.7},
            {"week": 2, "rs_ratio": 0.96, "rs_momentum": -3.2},
            {"week": 3, "rs_ratio": 0.97, "rs_momentum": -2.8},
            {"week": 4, "rs_ratio": 0.97, "rs_momentum": -2.3},
            {"week": 5, "rs_ratio": 0.98, "rs_momentum": -1.8},
            {"week": 6, "rs_ratio": 0.98, "rs_momentum": -1.2},
            {"week": 7, "rs_ratio": 0.99, "rs_momentum": -0.7},
            {"week": 8, "rs_ratio": 0.99, "rs_momentum": -0.1},
            {"week": 9, "rs_ratio": 1.00, "rs_momentum": 0.5},
        ],
    },
]

# Options Flow & Gamma Exposure mock data
MOCK_OPTIONS_FLOW = {
    "timestamp": datetime.utcnow().isoformat(),
    "ticker": "SPY",
    "spot_price": 575.82,
    "iv_skew": 0.15,  # Slight put skew
    "put_call_ratio": 1.08,  # Slightly more puts
    "volume_imbalance": 0.95,  # Slightly more puts
    "gex_signal": "positive",
    "gex_value": 125.5,
    "total_call_volume": 4250000,
    "total_put_volume": 4590000,
    "total_call_oi": 12500000,
    "total_put_oi": 13200000,
    "signal": "neutral",
    "details": [
        "Slightly elevated put volume (1.08x ratio)",
        "Put skew present (IV skew: 0.15)",
        "GEX positive (125.5)",
        "Balanced call-put dynamic",
    ],
    "expiry": "2026-03-21",
}

# Cross-Asset Momentum Spillover mock data
MOCK_MOMENTUM_SPILLOVER = {
    "timestamp": datetime.utcnow().isoformat(),
    "assets": [
        {
            "ticker": "SPY",
            "name": "S&P 500",
            "asset_class": "Equities",
            "momentum_1m": 0.0325,
            "momentum_3m": 0.0845,
            "state": "positive",
        },
        {
            "ticker": "TLT",
            "name": "US Bonds (7-10yr)",
            "asset_class": "Fixed Income",
            "momentum_1m": 0.0182,
            "momentum_3m": 0.0421,
            "state": "positive",
        },
        {
            "ticker": "GLD",
            "name": "Gold",
            "asset_class": "Commodities",
            "momentum_1m": 0.0125,
            "momentum_3m": 0.0312,
            "state": "positive",
        },
        {
            "ticker": "USO",
            "name": "Oil",
            "asset_class": "Commodities",
            "momentum_1m": -0.0245,
            "momentum_3m": 0.0156,
            "state": "neutral",
        },
        {
            "ticker": "UUP",
            "name": "US Dollar",
            "asset_class": "Currencies",
            "momentum_1m": -0.0165,
            "momentum_3m": -0.0082,
            "state": "negative",
        },
        {
            "ticker": "BTC-USD",
            "name": "Bitcoin",
            "asset_class": "Crypto",
            "momentum_1m": 0.1250,
            "momentum_3m": 0.2850,
            "state": "positive",
        },
    ],
    "signals": [
        {
            "description": "Bond momentum positive — equity outlook favorable",
            "type": "bullish",
            "confidence": 0.7,
            "based_on": ["TLT"],
        },
        {
            "description": "Broad momentum alignment: Multiple asset classes rallying",
            "type": "bullish",
            "confidence": 0.75,
            "based_on": ["SPY", "TLT", "GLD", "BTC-USD"],
        },
    ],
    "matrix": {
        "positive_count": 4,
        "negative_count": 1,
        "neutral_count": 1,
    },
}

# VIX Term Structure mock data
MOCK_VIX_TERM_STRUCTURE = {
    "vix_spot": 15.45,
    "vix3m": 15.82,
    "ratio": 1.024,
    "state": "contango",
    "magnitude": 2.4,
    "percentile": 38,
    "roll_yield": 0.0018,
    "signal": "bullish",
    "history": [
        {"date": "2026-02-03", "ratio": 1.018, "vix": 15.20},
        {"date": "2026-02-04", "ratio": 1.019, "vix": 15.25},
        {"date": "2026-02-05", "ratio": 1.020, "vix": 15.30},
        {"date": "2026-02-06", "ratio": 1.021, "vix": 15.32},
        {"date": "2026-02-07", "ratio": 1.022, "vix": 15.35},
        {"date": "2026-02-10", "ratio": 1.023, "vix": 15.38},
        {"date": "2026-02-11", "ratio": 1.023, "vix": 15.40},
        {"date": "2026-02-12", "ratio": 1.024, "vix": 15.42},
        {"date": "2026-02-13", "ratio": 1.025, "vix": 15.45},
        {"date": "2026-03-01", "ratio": 1.018, "vix": 15.20},
        {"date": "2026-03-02", "ratio": 1.021, "vix": 15.35},
        {"date": "2026-03-03", "ratio": 1.023, "vix": 15.40},
        {"date": "2026-03-04", "ratio": 1.025, "vix": 15.45},
        {"date": "2026-03-05", "ratio": 1.024, "vix": 15.45},
    ]
}

# Upgraded regime detection mock data
MOCK_UPGRADED_REGIME = {
    "regime": "bull",
    "confidence": 72,
    "bull_score": 4,
    "bear_score": 1,
    "signals": [
        {"name": "VIX", "value": "15.5", "reading": "Normal", "bias": "bull"},
        {"name": "Yield Curve", "value": "-0.40%", "reading": "Positive", "bias": "bull"},
        {"name": "S&P 500", "value": "+1.49%", "reading": "Rallying", "bias": "bull"},
        {"name": "Haven Demand", "value": "$2915", "reading": "Low", "bias": "bull"},
    ],
    "recession_probability": 22.5,
    "correlation_regime": "normal",
    "macro_surprise_score": 0.35,
}
