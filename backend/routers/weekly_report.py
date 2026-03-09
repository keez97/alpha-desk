from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from datetime import datetime
import json
from backend.database import get_session
from backend.models.report import WeeklyReport
from backend.services.claude_service import generate_weekly_report

router = APIRouter(prefix="/api/weekly-report", tags=["weekly-report"])


async def event_generator(end_date: str):
    """Generate SSE events for streaming report."""
    async for chunk in await generate_weekly_report(end_date):
        yield f"data: {json.dumps({'chunk': chunk})}\n\n"


@router.post("/generate")
async def generate_report(session: Session = Depends(get_session)):
    """Generate weekly report with streaming."""
    today = datetime.utcnow().date().isoformat()

    async def stream_report():
        full_report = ""
        async for chunk in await generate_weekly_report(today):
            full_report += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # Save to database
        try:
            report_json = json.loads(full_report)
            summary = report_json.get("market_overview", {}).get("summary", "")
        except (json.JSONDecodeError, TypeError):
            report_json = {"raw": full_report}
            summary = "See raw report"

        report = WeeklyReport(
            data_as_of=datetime.utcnow(),
            report_json=json.dumps(report_json),
            summary=summary
        )
        session.add(report)
        session.commit()

        yield f"data: {json.dumps({'complete': True, 'id': report.id})}\n\n"

    return StreamingResponse(
        stream_report(),
        media_type="text/event-stream"
    )


@router.get("/list")
def list_reports(session: Session = Depends(get_session)):
    """List all saved reports."""
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

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "reports": items
    }


@router.get("/{report_id}")
def get_report(report_id: int, session: Session = Depends(get_session)):
    """Get full report by ID."""
    report = session.get(WeeklyReport, report_id)

    if not report:
        return {"error": "Report not found"}, 404

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "id": report.id,
        "generated_at": report.generated_at.isoformat(),
        "data_as_of": report.data_as_of.isoformat(),
        "summary": report.summary,
        "report": json.loads(report.report_json)
    }


@router.delete("/{report_id}")
def delete_report(report_id: int, session: Session = Depends(get_session)):
    """Delete report by ID."""
    report = session.get(WeeklyReport, report_id)

    if not report:
        return {"error": "Report not found"}, 404

    session.delete(report)
    session.commit()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "deleted": report_id
    }
