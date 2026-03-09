from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class WeeklyReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    data_as_of: datetime
    report_json: str
    summary: Optional[str] = None
