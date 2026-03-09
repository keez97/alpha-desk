from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class PortfolioHolding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolio.id")
    ticker: str
    weight: Optional[float] = None


class Portfolio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    capital: float = Field(default=100000.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    holdings: List[PortfolioHolding] = Relationship()
