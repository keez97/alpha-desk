from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Watchlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(unique=True, index=True)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    last_grade: Optional[str] = None
    last_grade_at: Optional[datetime] = None
