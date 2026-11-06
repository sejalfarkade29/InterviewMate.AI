import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.api import (analytics, attempts, auth, code, daily, gd, health, history, jobmatch, practice, profile,
                     resume, rewards, roadmap, simulation, voice)
from app.core.config import settings
from app.database.base import Base
from app.database.session import engine

log = logging.getLogger("interviewmate")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creates any missing tables, so the app works on a fresh database without running Alembic first.
    # (create_all never alters or drops existing tables; Alembic stays the tool for schema changes.)
    Base.metadata.create_all(engine)
    log.info("Database ready (%s)", engine.url.render_as_string(hide_password=True))
    yield


app = FastAPI(title=settings.APP_NAME, version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Any local dev origin works too, so opening the site as 127.0.0.1:3000 or on another port does not break login.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Server error. Check the backend terminal for details."})


for module in (health, auth, profile, attempts, resume, jobmatch, practice, daily, code, voice, gd, simulation,
               analytics, roadmap, rewards, history):
    app.include_router(module.router, prefix="/api")
