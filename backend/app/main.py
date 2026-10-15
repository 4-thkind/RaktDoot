import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from .api import admin, auth, requests, stock, whatsapp_routes
from .config import settings
from .db import init_db, session_scope
from .jobs import ticker
from .models import BloodBank, Donor
from .seed import seed_blood_banks, seed_donors

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with session_scope() as db:  # first run: seed so the demo works out of the box
        if not db.scalar(select(func.count()).select_from(BloodBank)):
            seed_blood_banks(db)
        if not db.scalar(select(func.count()).select_from(Donor)):
            seed_donors(db)
    task = asyncio.create_task(ticker.run_forever())
    yield
    task.cancel()


app = FastAPI(title="Rakt Doot API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, stock.router, requests.router, whatsapp_routes.router, admin.router):
    app.include_router(r)
