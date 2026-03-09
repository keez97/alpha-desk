#!/usr/bin/env python3
"""
Seed the AlphaDesk database with initial data.

This script loads:
1. Fama-French 5-factor data
2. Sample securities (S&P 500 top companies)
3. Initial price history
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pandas as pd
import yfinance as yf
from sqlmodel import Session, create_engine, select

# Import models from backend
from backend.models import (
    Security,
    PriceHistory,
    Factor,
    FactorExposure,
)

def get_db_session():
    """Get database session."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://alphadesk:alphadesk_dev@localhost:5432/alphadesk"
    )
    engine = create_engine(database_url, echo=False)
    return Session(engine)

def seed_fama_french_factors(session: Session):
    """Seed Fama-French 5-factor data."""
    print("Loading Fama-French factors...")

    # Define the five factors
    factors = [
        {
            "name": "Market Risk (Mkt-RF)",
            "symbol": "MKT",
            "description": "Market risk premium (Market return - Risk-free rate)",
        },
        {
            "name": "Size (SMB)",
            "symbol": "SMB",
            "description": "Small Minus Big - return difference between small and large cap stocks",
        },
        {
            "name": "Value (HML)",
            "symbol": "HML",
            "description": "High Minus Low - return difference between high and low book-to-market stocks",
        },
        {
            "name": "Profitability (RMW)",
            "symbol": "RMW",
            "description": "Robust Minus Weak - return difference between high and low profitability stocks",
        },
        {
            "name": "Investment (CMA)",
            "symbol": "CMA",
            "description": "Conservative Minus Aggressive - return difference based on investment patterns",
        },
    ]

    for factor_data in factors:
        # Check if factor already exists
        existing = session.exec(
            select(Factor).where(Factor.symbol == factor_data["symbol"])
        ).first()

        if not existing:
            factor = Factor(**factor_data)
            session.add(factor)
            print(f"  Added factor: {factor_data['name']}")

    session.commit()
    print("Fama-French factors loaded successfully.")

def seed_sample_securities(session: Session):
    """Seed sample securities from S&P 500."""
    print("\nLoading sample securities...")

    # Top 50 S&P 500 companies by market cap
    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "META",
        "TSLA", "BRK.B", "JNJ", "V", "WMT",
        "JPM", "MA", "PG", "AVGO", "HD",
        "COST", "KO", "NFLX", "ABBV", "XOM",
        "ACN", "ORCL", "CRM", "IBM", "CSCO",
        "AMD", "ADBE", "TXN", "QCOM", "GS",
        "MCD", "AXP", "BA", "INTC", "CMCSA",
        "DIS", "GILD", "HON", "PANW", "INTU",
        "NOW", "SBUX", "PYPL", "AMAT", "ASML",
        "ELV", "LLY", "MRK", "CVX", "RTX",
    ]

    added_count = 0
    for ticker in sample_tickers:
        # Check if security already exists
        existing = session.exec(
            select(Security).where(Security.ticker == ticker)
        ).first()

        if existing:
            print(f"  {ticker} already exists, skipping")
            continue

        try:
            # Fetch basic info from yfinance
            info = yf.Ticker(ticker).info
            company_name = info.get("longName", ticker)
            sector = info.get("sector", "Unknown")
            industry = info.get("industry", "Unknown")

            security = Security(
                ticker=ticker,
                company_name=company_name,
                sector=sector,
                industry=industry,
                exchange="NASDAQ" if sector else "NYSE",
            )
            session.add(security)
            added_count += 1
            print(f"  Added: {ticker} - {company_name}")

        except Exception as e:
            print(f"  Warning: Could not fetch data for {ticker}: {e}")

    session.commit()
    print(f"Loaded {added_count} sample securities.")

def seed_price_history(session: Session, days: int = 250):
    """Seed price history for sample securities."""
    print(f"\nLoading price history (last {days} trading days)...")

    # Get all securities
    securities = session.exec(select(Security)).all()

    if not securities:
        print("  No securities found. Run seed_sample_securities first.")
        return

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    added_count = 0
    for security in securities:
        try:
            # Check if we already have price data
            existing = session.exec(
                select(PriceHistory).where(
                    PriceHistory.security_id == security.id
                )
            ).first()

            if existing:
                print(f"  {security.ticker} already has price history, skipping")
                continue

            # Fetch price data
            data = yf.download(
                security.ticker,
                start=start_date,
                end=end_date,
                progress=False,
            )

            if data.empty:
                print(f"  Warning: No price data for {security.ticker}")
                continue

            # Insert price history
            for date, row in data.iterrows():
                price_entry = PriceHistory(
                    security_id=security.id,
                    date=date.date(),
                    open_price=float(row["Open"]),
                    high_price=float(row["High"]),
                    low_price=float(row["Low"]),
                    close_price=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
                session.add(price_entry)

            session.commit()
            added_count += 1
            print(f"  Loaded {len(data)} prices for {security.ticker}")

        except Exception as e:
            print(f"  Warning: Could not load price data for {security.ticker}: {e}")

    print(f"Price history loaded for {added_count} securities.")

def main():
    """Run all seed functions."""
    print("=" * 50)
    print("AlphaDesk Database Seeding")
    print("=" * 50)
    print()

    try:
        session = get_db_session()

        # Seed all data
        seed_fama_french_factors(session)
        seed_sample_securities(session)
        seed_price_history(session, days=250)

        session.close()

        print("\n" + "=" * 50)
        print("Seeding completed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
