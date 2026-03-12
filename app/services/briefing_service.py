from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.briefing import Briefing, BriefingMetric, BriefingPoint
from app.schemas.briefing import BriefingCreate


def create_briefing(db: Session, payload: BriefingCreate) -> Briefing:
    briefing = Briefing(
        company_name=payload.companyName.strip(),
        ticker=payload.ticker,  # already normalised by validator
        sector=payload.sector.strip(),
        analyst_name=payload.analystName.strip(),
        summary=payload.summary.strip(),
        recommendation=payload.recommendation.strip(),
    )
    db.add(briefing)
    db.flush()  # get briefing.id before inserting children

    for order, text in enumerate(payload.keyPoints):
        db.add(BriefingPoint(
            briefing_id=briefing.id,
            point_type="key_point",
            content=text,
            display_order=order,
        ))

    for order, text in enumerate(payload.risks):
        db.add(BriefingPoint(
            briefing_id=briefing.id,
            point_type="risk",
            content=text,
            display_order=order,
        ))

    for order, metric in enumerate(payload.metrics):
        db.add(BriefingMetric(
            briefing_id=briefing.id,
            name=metric.name.strip(),
            value=metric.value.strip(),
            display_order=order,
        ))

    db.commit()
    db.refresh(briefing)
    return _load_with_relations(db, briefing.id)


def get_briefing(db: Session, briefing_id: uuid.UUID) -> Briefing | None:
    return _load_with_relations(db, briefing_id)


def mark_generated(db: Session, briefing: Briefing) -> Briefing:
    briefing.is_generated = True
    briefing.generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(briefing)
    return briefing


def _load_with_relations(db: Session, briefing_id: uuid.UUID) -> Briefing | None:
    stmt = (
        select(Briefing)
        .where(Briefing.id == briefing_id)
        .options(
            selectinload(Briefing.points),
            selectinload(Briefing.metrics),
        )
    )
    return db.scalar(stmt)