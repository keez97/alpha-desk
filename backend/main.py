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
    settings,
    backtester,
    factors,
    data_ingestion
)

app = FastAPI(
    title="AlphaDesk API",
    description="Investment dashboard backend API",
    version="1.0.0"
)

# CORS middleware - restrict to local development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(morning_brief.router)
app.include_router(stock.router)
app.include_router(watchlist.router)
app.include_router(screener.router)
app.include_router(weekly_report.router)
app.include_router(portfolio.router)
app.include_router(rrg.router)
app.include_router(settings.router)
app.include_router(backtester.router)
app.include_router(factors.router)
app.include_router(data_ingestion.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
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
