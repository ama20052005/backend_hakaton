from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.models import ReportFormat, ReportGenerationRequest, ReportGenerationResponse
from app.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(request: ReportGenerationRequest):
    """Собирает аналитическую справку и формирует файлы выгрузки."""

    return await report_service.generate_report(request)


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: ReportFormat = Query(...),
):
    """Скачивает ранее сгенерированный файл справки."""

    if format == ReportFormat.BOTH:
        raise HTTPException(status_code=400, detail="Use format=docx or format=pdf")

    file_path = report_service.get_report_file_path(report_id, format)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == ReportFormat.DOCX
        else "application/pdf"
    )
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
    )
