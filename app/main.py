from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.db import SessionLocal, init_db
from app.services.setup import ensure_defaults_setup
from app.logging import get_logger
from app.api import health, teams, sync, metrics, plans

log = get_logger("main")

app = FastAPI(title="EM-Aide")

app.include_router(health.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(plans.router, prefix="/api")

UI_DIST = "/app/ui-dist"
if os.path.isdir(UI_DIST):
    # Serve the React app at /app (single-origin, no CORS)
    app.mount("/app", StaticFiles(directory=UI_DIST, html=True), name="ui")

    @app.get("/app/{full_path:path}")
    def spa_fallback(full_path: str):
        index_path = os.path.join(UI_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "UI not built"}
    

@app.on_event("startup")
def _startup():
    init_db()
    # Create default org/team and configs from env
    db = SessionLocal()
    try:
        ensure_defaults_setup(db)
    finally:
        db.close()
