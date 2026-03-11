from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from backend.database import create_db_and_tables
from backend.routers import (
    morning_brief,
    stock,
    watchlist,
    screener,
    weekly_report,
    portfolio,
    rrg,
    rotation_alerts,
    settings,
    backtester,
    factors,
    data_ingestion,
    events,
    earnings,
    sentiment,
    sentiment_velocity,
    cot_positioning,
    confluence,
    confluence_backtest,
    quant_screener,
    quick_backtest,
    enhanced_sectors,
    position_sizing,
    notifications,
    intraday_momentum,
    correlation,
    earnings_confluence,
    overnight_returns,
    earnings_brief,
    options_flow,
    cross_asset_momentum,
    sector_transitions,
    scenario_risk,
    vix_term_structure,
)

app = FastAPI(
    title="AlphaDesk API",
    description="Investment dashboard backend API",
    version="1.0.0",
)

# CORS middleware
import os as _os
_allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
]
# Add production frontend URL from env
_frontend_url = _os.getenv("FRONTEND_URL", "")
if _frontend_url:
    _allowed_origins.append(_frontend_url)
# Also allow any *.vercel.app subdomain during development
_allowed_origins.append("https://*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# GZip compression for responses > 500 bytes
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)

# Include routers
app.include_router(morning_brief.router)
app.include_router(stock.router)
app.include_router(watchlist.router)
app.include_router(screener.router)
app.include_router(weekly_report.router)
app.include_router(portfolio.router)
app.include_router(rrg.router)
app.include_router(rotation_alerts.router)
app.include_router(settings.router)
app.include_router(backtester.router)
app.include_router(factors.router)
app.include_router(data_ingestion.router)
app.include_router(events.router)
app.include_router(earnings.router)
app.include_router(sentiment.router)
app.include_router(sentiment_velocity.router)
app.include_router(cot_positioning.router)
app.include_router(confluence.router)
app.include_router(confluence_backtest.router)
app.include_router(quant_screener.router)
app.include_router(quick_backtest.router)
app.include_router(enhanced_sectors.router)
app.include_router(position_sizing.router)
app.include_router(notifications.router)
app.include_router(intraday_momentum.router)
app.include_router(correlation.router)
app.include_router(earnings_confluence.router)
app.include_router(overnight_returns.router)
app.include_router(earnings_brief.router)
app.include_router(options_flow.router)
app.include_router(cross_asset_momentum.router)
app.include_router(sector_transitions.router)
app.include_router(scenario_risk.router)
app.include_router(vix_term_structure.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()

    # Start background cache refresh daemon (replaces one-shot _prewarm)
    from backend.services import cache_refresh
    cache_refresh.start()


@app.on_event("shutdown")
def on_shutdown():
    from backend.services import cache_refresh
    cache_refresh.stop()


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/cache/stats")
def cache_stats():
    """Get data cache statistics."""
    from backend.services.cache import cache
    return {
        "cache": cache.stats(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/data/health")
def data_health():
    """Check data provider tier availability."""
    from backend.services import fds_client, fred_client
    from backend.config import FDS_API_KEY, FRED_API_KEY
    return {
        "tiers": {
            "tier1_fds": {"available": fds_client.is_available(), "key_set": bool(FDS_API_KEY)},
            "tier2_fred": {"available": bool(FRED_API_KEY), "key_set": bool(FRED_API_KEY)},
            "tier3_yfinance": {"available": True, "key_set": True},
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "AlphaDesk API",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# trigger host reload 1773104864
