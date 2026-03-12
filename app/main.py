from fastapi import FastAPI

from app.api.briefings import router as briefings_router
from app.api.health import router as health_router
from app.api.sample_items import router as sample_items_router

app = FastAPI(title="InsightOps", version="0.2.0")

app.include_router(health_router)
app.include_router(sample_items_router)
app.include_router(briefings_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "InsightOps", "status": "ready"}