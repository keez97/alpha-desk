from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class MorningBriefCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cache_key: str = Field(unique=True, index=True)
    data_json: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class StockGradeCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    grade_json: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ScreenerCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    screen_type: str = Field(index=True)
    results_json: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
