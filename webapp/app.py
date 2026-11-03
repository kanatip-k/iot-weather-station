"""
Web Application (FastAPI)
--------------------------
Serves:
  - Web API   : /api/stations, /api/stations/{id}/latest, /api/stations/{id}/history
  - Dashboard : / (static HTML/JS, polling-based auto refresh)
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "weather_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "weather_readings")
ONLINE_THRESHOLD_SECONDS = int(os.getenv("ONLINE_THRESHOLD_SECONDS", "30"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [webapp] %(levelname)s: %(message)s",
)
log = logging.getLogger("webapp")

app = FastAPI(title="IoT Weather & Air Quality Monitoring API")

client: Optional[MongoClient] = None
collection = None


def get_collection():
    """Lazily (re)connect to MongoDB; never lets a DB outage crash the app."""
    global client, collection
    if collection is not None:
        return collection
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        collection = client[MONGO_DB_NAME][MONGO_COLLECTION]
        log.info("Connected to MongoDB at %s", MONGO_URL)
        return collection
    except PyMongoError as e:
        log.error("MongoDB connection error: %s", e)
        collection = None
        return None


def serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("received_at"), datetime):
        doc["received_at"] = doc["received_at"].isoformat()
    return doc


@app.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/stations")
def list_stations():
    """FR-15 — List all known stations."""
    col = get_collection()
    if col is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        stations = col.distinct("station_id")
        return sorted(stations)
    except PyMongoError as e:
        log.error("Database error in list_stations: %s", e)
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/api/stations/{station_id}/latest")
def get_latest(station_id: str):
    """FR-13 — Latest Data Query: filter station -> sort received_at DESC -> limit 1."""
    col = get_collection()
    if col is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        doc = col.find_one({"station_id": station_id}, sort=[("received_at", DESCENDING)])
    except PyMongoError as e:
        log.error("Database error in get_latest: %s", e)
        raise HTTPException(status_code=500, detail="Database error")

    if doc is None:
        raise HTTPException(status_code=404, detail=f"No data found for station '{station_id}'")

    result = serialize(doc)

    # FR-19 Station Status
    try:
        received_dt = datetime.fromisoformat(result["received_at"])
        now = datetime.now(received_dt.tzinfo or timezone.utc)
        age = (now - received_dt).total_seconds()
        result["status"] = "ONLINE" if age <= ONLINE_THRESHOLD_SECONDS else "OFFLINE"
    except Exception:
        result["status"] = "UNKNOWN"

    return result


@app.get("/api/stations/{station_id}/history")
def get_history(station_id: str, limit: int = Query(default=50, ge=1, le=1000)):
    """FR-14 — Historical Data Query, supports ?limit=N (10 / 50 / 100 ...)."""
    col = get_collection()
    if col is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        cursor = col.find({"station_id": station_id}).sort("received_at", DESCENDING).limit(limit)
        docs = [serialize(d) for d in cursor]
    except PyMongoError as e:
        log.error("Database error in get_history: %s", e)
        raise HTTPException(status_code=500, detail="Database error")

    if not docs:
        # Empty result per SRS ("Return Empty Result/404 as per design") — we return empty list + 200
        return []

    docs.reverse()  # chronological order for charting
    return docs


# ---------------------------------------------------------------------------
# Dashboard (static files)
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def dashboard():
    return FileResponse("static/index.html")
