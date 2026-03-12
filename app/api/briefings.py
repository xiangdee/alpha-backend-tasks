from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.briefing import BriefingCreate, BriefingRead, GenerateResponse
from app.services import briefing_report_formatter as formatter_module
from app.services import briefing_service

router = APIRouter(prefix="/briefings", tags=["briefings"])

_formatter = formatter_module.BriefingReportFormatter()


@router.post("", response_model=BriefingRead, status_code=status.HTTP_201_CREATED)
def create_briefing(
    payload: BriefingCreate,
    db: Annotated[Session, Depends(get_db)],
) -> BriefingRead:
    briefing = briefing_service.create_briefing(db, payload)
    return BriefingRead.model_validate(briefing)


@router.get("/{briefing_id}", response_model=BriefingRead)
def get_briefing(
    briefing_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> BriefingRead:
    briefing = briefing_service.get_briefing(db, briefing_id)
    if not briefing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Briefing not found")
    return BriefingRead.model_validate(briefing)


@router.post("/{briefing_id}/generate", response_model=GenerateResponse)
def generate_report(
    briefing_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> GenerateResponse:
    briefing = briefing_service.get_briefing(db, briefing_id)
    if not briefing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Briefing not found")

    briefing = briefing_service.mark_generated(db, briefing)

    return GenerateResponse(
        id=briefing.id,
        is_generated=briefing.is_generated,
        generated_at=briefing.generated_at,
        message="Report generated successfully.",
    )


@router.get("/{briefing_id}/html")
def get_report_html(
    briefing_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    briefing = briefing_service.get_briefing(db, briefing_id)
    if not briefing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Briefing not found")
    if not briefing.is_generated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report has not been generated yet. POST /briefings/{id}/generate first.",
        )

    html = _formatter.render_html(briefing)
    return Response(content=html, media_type="text/html")