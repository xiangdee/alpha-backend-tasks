import os
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.config import get_settings
get_settings.cache_clear()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.briefing import Briefing, BriefingMetric, BriefingPoint  # type: ignore # noqa: F401
from app.models.sample_item import SampleItem  # type: ignore # noqa: F401

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

import app.db.session as _session_module
_session_module.engine = test_engine
_session_module.SessionLocal = TestSessionLocal

Base.metadata.create_all(bind=test_engine)