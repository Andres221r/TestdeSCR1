from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from requests import RequestException

from app import db
from app.collector import (
    RobloxCollector,
    ensure_milestones,
    store_snapshot,
    update_prediction_for_next_milestone,
)
from app.predict import predict_milestone_date
from app.settings import SETTINGS

app = FastAPI(title="Roblox Insights")

collector = RobloxCollector()


def collect_and_update() -> None:
    try:
        snapshot = collector.fetch_game_snapshot()
    except RequestException as exc:
        print(f"[collector] Error fetching Roblox data: {exc}")
        return
    except Exception as exc:
        print(f"[collector] Unexpected error: {exc}")
        return

    store_snapshot(SETTINGS.db_path, snapshot)
    ensure_milestones(SETTINGS.db_path, SETTINGS.milestone_step, snapshot.visits)
    prediction = predict_milestone_date(SETTINGS.db_path)
    update_prediction_for_next_milestone(SETTINGS.db_path, prediction.predicted_at)


@app.on_event("startup")
def startup() -> None:
    db.init_db(SETTINGS.db_path)
    collect_and_update()
    scheduler = BackgroundScheduler()
    scheduler.add_job(collect_and_update, "interval", seconds=SETTINGS.data_refresh_seconds)
    scheduler.start()
    app.state.scheduler = scheduler


@app.on_event("shutdown")
def shutdown() -> None:
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown()


app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent.parent / "web"), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = Path(__file__).resolve().parent.parent / "web" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/latest")
def latest_snapshot() -> dict:
    row = db.fetchone(
        SETTINGS.db_path,
        """
        SELECT * FROM snapshots ORDER BY collected_at DESC LIMIT 1
        """,
    )
    if not row:
        return {"status": "no_data"}
    return {
        "collected_at": row["collected_at"],
        "name": row["name"],
        "visits": row["visits"],
        "playing": row["playing"],
        "favorites": row["favorites"],
        "up_votes": row["up_votes"],
        "down_votes": row["down_votes"],
        "version": row["version"],
    }


@app.get("/api/milestones")
def milestones() -> dict:
    rows = db.fetchall(
        SETTINGS.db_path,
        """
        SELECT target_visits, achieved_at, predicted_at, created_at
        FROM milestones
        ORDER BY target_visits ASC
        """,
    )
    return {
        "milestones": [
            {
                "target_visits": row["target_visits"],
                "achieved_at": row["achieved_at"],
                "predicted_at": row["predicted_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.get("/api/prediction")
def prediction() -> dict:
    prediction_data = predict_milestone_date(SETTINGS.db_path)
    return {
        "target_visits": prediction_data.target_visits,
        "predicted_at": prediction_data.predicted_at,
        "daily_growth": prediction_data.daily_growth,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/versions")
def versions() -> dict:
    rows = db.fetchall(
        SETTINGS.db_path,
        "SELECT version, detected_at FROM versions ORDER BY detected_at DESC",
    )
    return {
        "versions": [
            {"version": row["version"], "detected_at": row["detected_at"]} for row in rows
        ]
    }
