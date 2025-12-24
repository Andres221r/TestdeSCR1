from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app import db


@dataclass
class Prediction:
    target_visits: int
    predicted_at: Optional[str]
    daily_growth: Optional[float]


def predict_milestone_date(db_path: str) -> Prediction:
    milestone = db.fetchone(
        db_path,
        "SELECT target_visits FROM milestones WHERE achieved_at IS NULL ORDER BY target_visits ASC LIMIT 1",
    )
    if milestone is None:
        return Prediction(target_visits=0, predicted_at=None, daily_growth=None)

    snapshots = db.fetchall(
        db_path,
        """
        SELECT collected_at, visits
        FROM snapshots
        ORDER BY collected_at ASC
        """,
    )

    if len(snapshots) < 2:
        return Prediction(target_visits=int(milestone["target_visits"]), predicted_at=None, daily_growth=None)

    times = []
    visits = []
    for row in snapshots:
        collected_at = datetime.fromisoformat(row["collected_at"])
        if collected_at.tzinfo is None:
            collected_at = collected_at.replace(tzinfo=timezone.utc)
        times.append(collected_at.timestamp())
        visits.append(int(row["visits"]))

    t0 = times[0]
    xs = [t - t0 for t in times]
    ys = visits

    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denominator = (n * sum_x2) - (sum_x ** 2)
    if denominator == 0:
        return Prediction(target_visits=int(milestone["target_visits"]), predicted_at=None, daily_growth=None)

    slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
    intercept = (sum_y - slope * sum_x) / n

    target_visits = int(milestone["target_visits"])
    if slope <= 0:
        return Prediction(target_visits=target_visits, predicted_at=None, daily_growth=None)

    target_time = (target_visits - intercept) / slope
    predicted_timestamp = t0 + target_time
    predicted_at = datetime.fromtimestamp(predicted_timestamp, tz=timezone.utc).isoformat()

    daily_growth = slope * 86400
    return Prediction(target_visits=target_visits, predicted_at=predicted_at, daily_growth=daily_growth)
