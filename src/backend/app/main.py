import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quotebook")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    await asyncio.to_thread(sync.run_sync)

    stop_event = asyncio.Event()

    async def periodic_sync():
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=config.SYNC_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                await asyncio.to_thread(sync.run_sync)

    task = asyncio.create_task(periodic_sync())
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()


app = FastAPI(lifespan=lifespan)

api = APIRouter()


@api.get("/quotes/today")
def get_todays_quotes():
    used_date, is_fallback, quotes = db.query_today()
    return {"date": used_date, "is_fallback": is_fallback, "quotes": quotes}


@api.get("/quotes")
def get_quotes(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    quotes, total = db.query_quotes(q, page, page_size)
    return {"quotes": quotes, "total": total, "page": page, "page_size": page_size}


# API routes are registered before any static file mounts so nothing can
# shadow /api/*.
app.include_router(api, prefix="/api")


@app.get("/")
def serve_index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


@app.get("/all")
def serve_all():
    return FileResponse(config.FRONTEND_DIR / "all.html")


@app.get("/about")
def serve_about():
    return FileResponse(config.FRONTEND_DIR / "about.html")


app.mount("/css", StaticFiles(directory=config.FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=config.FRONTEND_DIR / "js"), name="js")
app.mount("/media", StaticFiles(directory=config.DATA_MEDIA_DIR), name="media")
