import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from .api import admin, ai, auth, mock_portal, requests, stock, whatsapp_routes
from .config import settings
from .db import init_db, session_scope
from .jobs import ticker
from .services import stt
from .models import BloodBank, Donor, GuideChunk
from .seed import seed_blood_banks, seed_donors, seed_extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with session_scope() as db:  # first run: seed so the demo works out of the box
        banks = db.scalars(select(BloodBank)).all()
        if banks and all(b.source.startswith("seed") for b in banks):
            for b in banks:  # upgrade the old hand-made list to the real eRaktKosh directory (W2)
                db.delete(b)
            db.flush()
            banks = []
        if not banks:
            seed_blood_banks(db)
        if not db.scalar(select(func.count()).select_from(Donor)):
            seed_donors(db)
            db.flush()
        if not db.scalar(select(func.count()).select_from(GuideChunk)):
            seed_extras(db)
    task = asyncio.create_task(ticker.run_forever())
    warm = asyncio.create_task(asyncio.to_thread(stt.warm))  # load (and on first run download) the local speech model
    yield
    task.cancel()
    warm.cancel()


app = FastAPI(title="Rakt Doot API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, stock.router, requests.router, whatsapp_routes.router, admin.router, ai.router, ai.hooks, mock_portal.router):
    app.include_router(r)
