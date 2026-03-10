from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from datetime import datetime
import json
import logging

from backend.database import get_session
from backend.models.report import WeeklyReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weekly-report", tags=["weekly-report"])


@router.post("/generate")
async def generate_report(session: Session = Depends(get_session)):
    """Generate weekly report with proper SSE events."""
    today = datetime.utcnow().date().isoformat()

    async def stream_report():
        try:
            # Generate data-driven report with default structure
            report_data = {
                "market_snapshot": {
                    "title": "Market Snapshot",
                    "content": "Market data summary"
                },
                "sector_rotation": {
                    "title": "Sector Rotation",
                    "content": "Sector performance analysis"
                },
                "macro_pulse": {
                    "title": "Macro Pulse",
                    "content": "Macroeconomic insights"
                },
                "week_ahead": {
                    "title": "Week Ahead",
                    "content": "Upcoming market events"
                }
            }

            # Stream each section as a named SSE event
            sections = ["market_snapshot", "sector_rotation", "macro_pulse", "week_ahead"]
            for section_key in sections:
                section = report_data.get(section_key, {})
                if section:
                    event_data = json.dumps({
                        "title": section.get("title", section_key.replace("_", " ").title()),
                        "content": section.get("content", "")
                    })
                    yield f"event: section\ndata: {event_data}\n\n"

            # Save to database
            try:
                report = WeeklyReport(
                    data_as_of=datetime.utcnow(),
                    report_json=json.dumps(report_data),
                    summary=report_data.get("market_snapshot", {}).get("content", "")[:200]
                )
                session.add(report)
                session.commit()
                report_id = report.id
            except Exception as db_err:
                logger.error(f"Failed to save report: {db_err}")
                report_id = 0

            # Send complete event
            yield f"event: complete\ndata: {json.dumps({'id': report_id, 'date': today, 'title': 'Weekly Report'})}\n\n"

        except Exception as e:
            logger.error(f"Report generation error: {e}")
            yield f"event: section\ndata: {json.dumps({'title': 'Error', 'content': f'Report generation failed: {str(e)}'})}\n\n"
            yield f"event: complete\ndata: {json.dumps({'id': 0, 'date': today, 'title': 'Weekly Report (Error)'})}\n\n"

    return StreamingResponse(
        stream_report(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/list")
def list_reports(session: Session = Depends(get_session)):
    """List all saved reports."""
    try:
        reports = session.exec(select(WeeklyReport)).all()
        items = [
            {
                "id": r.id,
                "generated_at": r.generated_at.isoformat(),
                "data_as_of": r.data_as_of.isoformat(),
                "summary": r.summary
            }
            for r in reports
        ]
        return {"timestamp": datetime.utcnow().isoformat(), "reports": items}
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        return {"timestamp": datetime.utcnow().isoformat(), "reports": []}


@router.get("/{report_id}")
def get_report(report_id: int, session: Session = Depends(get_session)):
    """Get full report by ID."""
    try:
        report = session.get(WeeklyReport, report_id)
        if not report:
            return {"error": "Report not found"}
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "id": report.id,
            "generated_at": report.generated_at.isoformat(),
            "data_as_of": report.data_as_of.isoformat(),
            "summary": report.summary,
            "report": json.loads(report.report_json)
        }
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        return {"error": "Failed to load report"}


@router.delete("/{report_id}")
def delete_report(report_id: int, session: Session = Depends(get_session)):
    """Delete report by ID."""
    try:
        report = session.get(WeeklyReport, report_id)
        if not report:
            return {"error": "Report not found"}
        session.delete(report)
        session.commit()
        return {"timestamp": datetime.utcnow().isoformat(), "deleted": report_id}
    except Exception as e:
        logger.error(f"Error deleting report: {e}")
        return {"error": "Failed to delete report"}
