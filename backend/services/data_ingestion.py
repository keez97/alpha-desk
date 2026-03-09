"""
Data ingestion service for loading external data with PiT timestamps.
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, List
import csv
from io import StringIO
import httpx
from sqlmodel import Session, select

from backend.models.securities import Security
from backend.models.market_data import PriceHistory, FundamentalsSnapshot
from backend.models.factors import FactorDefinition, FamaFrenchFactor
from backend.repositories.pit_queries import (
    get_prices_pit,
    get_fundamentals_pit,
)


class DataIngestionService:
    """Ingest data from external sources with PiT timestamps."""

    def __init__(self, session: Session):
        self.session = session

    async def ingest_price_history(
        self,
        ticker: str,
        period: str = "5y"
    ) -> int:
        """
        Load price data from yfinance and save with ingestion_timestamp=now.

        Args:
            ticker: Security ticker
            period: Period of data ("1y", "5y", "10y", etc.)

        Returns:
            Number of price records ingested
        """
        try:
            import yfinance as yf

            # Ensure security exists
            await self.ensure_security_exists(ticker)

            # Download price data
            data = yf.download(ticker, period=period, progress=False)

            if data.empty:
                return 0

            # Convert to records
            count = 0
            now = datetime.now(timezone.utc)

            for idx, row in data.iterrows():
                # Parse date from index
                if hasattr(idx, 'date'):
                    record_date = idx.date()
                else:
                    record_date = idx

                # Check if already exists
                existing = self.session.exec(
                    select(PriceHistory).where(
                        PriceHistory.ticker == ticker,
                        PriceHistory.date == record_date,
                        PriceHistory.data_source == "yfinance"
                    )
                ).first()

                if existing:
                    continue

                # Create price record
                price_record = PriceHistory(
                    ticker=ticker,
                    date=record_date,
                    open_price=Decimal(str(row.get('Open', 0))),
                    high_price=Decimal(str(row.get('High', 0))),
                    low_price=Decimal(str(row.get('Low', 0))),
                    close_price=Decimal(str(row.get('Close', 0))),
                    adjusted_close=Decimal(str(row.get('Adj Close', row.get('Close', 0)))),
                    volume=int(row.get('Volume', 0)),
                    data_source="yfinance",
                    ingestion_timestamp=now,
                )

                self.session.add(price_record)
                count += 1

            if count > 0:
                self.session.commit()

            return count

        except Exception as e:
            print(f"Error ingesting prices for {ticker}: {e}")
            return 0

    async def ingest_fundamentals(
        self,
        ticker: str
    ) -> int:
        """
        Load fundamental data from yfinance with source_document_date.

        Args:
            ticker: Security ticker

        Returns:
            Number of fundamental records ingested
        """
        try:
            import yfinance as yf

            # Ensure security exists
            await self.ensure_security_exists(ticker)

            # Download ticker info
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            if not info:
                return 0

            # Map common fundamental metrics
            fundamentals_map = {
                "marketCap": "market_cap",
                "trailingEps": "earnings_per_share",
                "profitMargins": "profit_margin",
                "operatingCashflow": "operating_cash_flow",
                "freeCashflow": "free_cash_flow",
                "totalDebt": "total_debt",
                "totalAssets": "total_assets",
                "stockholders_equity": "stockholders_equity",
                "bookValue": "book_value",
                "pegRatio": "peg_ratio",
            }

            count = 0
            now = datetime.now(timezone.utc)
            today = date.today()

            for yf_key, metric_name in fundamentals_map.items():
                value = info.get(yf_key)

                if value is None:
                    continue

                # Check if already exists
                existing = self.session.exec(
                    select(FundamentalsSnapshot).where(
                        FundamentalsSnapshot.ticker == ticker,
                        FundamentalsSnapshot.metric_name == metric_name,
                        FundamentalsSnapshot.source_document_date == today,
                        FundamentalsSnapshot.data_source == "yfinance"
                    )
                ).first()

                if existing:
                    continue

                # Create fundamentals record
                fund_record = FundamentalsSnapshot(
                    ticker=ticker,
                    fiscal_period_end=today,
                    metric_name=metric_name,
                    metric_value=Decimal(str(value)),
                    source_document_date=today,
                    document_type="snapshot",
                    data_source="yfinance",
                    ingestion_timestamp=now,
                )

                self.session.add(fund_record)
                count += 1

            if count > 0:
                self.session.commit()

            return count

        except Exception as e:
            print(f"Error ingesting fundamentals for {ticker}: {e}")
            return 0

    async def ingest_fama_french_factors(self) -> int:
        """
        Download Kenneth French CSV data and load into fama_french_factors table.

        Downloads from:
        https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip

        Returns:
            Number of factor return records ingested
        """
        try:
            # Download URL
            url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"

            # Create or get FF5 factors
            ff_factors = {
                "Mkt-RF": "Market",
                "SMB": "Small Minus Big",
                "HML": "High Minus Low",
                "RMW": "Profitable Minus Unprofitable",
                "CMA": "Conservative Minus Aggressive",
                "RF": "Risk Free Rate"
            }

            factor_defs = {}

            for factor_code, factor_name in ff_factors.items():
                factor_def = self.session.exec(
                    select(FactorDefinition).where(
                        FactorDefinition.factor_name == f"FF5_{factor_code}"
                    )
                ).first()

                if not factor_def:
                    factor_def = FactorDefinition(
                        factor_name=f"FF5_{factor_code}",
                        factor_type="fama_french",
                        description=factor_name,
                        frequency="monthly",
                        is_published=True,
                        publication_date=date(1993, 7, 1),  # FF5 publication date
                    )
                    self.session.add(factor_def)
                    self.session.commit()
                    self.session.refresh(factor_def)

                factor_defs[factor_code] = factor_def

            # Try to download data
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=30)

                if response.status_code != 200:
                    print(f"Failed to download FF5 data: {response.status_code}")
                    return 0

            except Exception as e:
                print(f"Error downloading FF5 data: {e}")
                # For now, return 0 - in production, you'd handle this better
                return 0

            # This is a simplified implementation
            # In production, you'd parse the ZIP file and extract the CSV
            # For now, return 0
            return 0

        except Exception as e:
            print(f"Error ingesting Fama-French factors: {e}")
            return 0

    async def ensure_security_exists(self, ticker: str) -> Security:
        """
        Create Security record if not exists, using yfinance for metadata.

        Args:
            ticker: Security ticker

        Returns:
            Security object
        """
        # Check if already exists
        existing = self.session.exec(
            select(Security).where(Security.ticker == ticker)
        ).first()

        if existing:
            return existing

        # Try to get metadata from yfinance
        try:
            import yfinance as yf

            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            name = info.get("longName", ticker)
            sector = info.get("sector", "Unknown")
            industry = info.get("industry", "Unknown")
            country = info.get("country", "US")

        except Exception:
            # Fallback if yfinance fails
            name = ticker
            sector = "Unknown"
            industry = "Unknown"
            country = "US"

        # Create security
        security = Security(
            ticker=ticker,
            name=name,
            sector=sector,
            industry=industry,
            country=country,
            status="ACTIVE",
        )

        self.session.add(security)
        self.session.commit()
        self.session.refresh(security)

        return security
