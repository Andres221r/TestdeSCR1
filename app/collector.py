from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Optional

import requests

from app import db
from app.settings import SETTINGS


UNIVERSE_LOOKUP_URL = "https://apis.roblox.com/universes/v1/places/{place_id}/universe"
GAME_DETAILS_URL = "https://games.roblox.com/v1/games"
GAME_VOTES_URL = "https://games.roblox.com/v1/games/votes"

VERSION_PATTERN = re.compile(r"v?(\d+\.\d+\.\d+)", re.IGNORECASE)


@dataclass
class GameSnapshot:
    universe_id: int
    name: str
    visits: int
    playing: int
    favorites: int
    up_votes: int
    down_votes: int
    version: Optional[str]


class RobloxCollector:
    def __init__(self, place_id: int = SETTINGS.place_id):
        self.place_id = place_id

    def fetch_universe_id(self) -> int:
        response = requests.get(UNIVERSE_LOOKUP_URL.format(place_id=self.place_id), timeout=10)
        response.raise_for_status()
        data = response.json()
        return int(data["universeId"])

    def fetch_game_snapshot(self) -> GameSnapshot:
        universe_id = self.fetch_universe_id()
        game_response = requests.get(
            GAME_DETAILS_URL,
            params={"universeIds": universe_id},
            timeout=10,
        )
        game_response.raise_for_status()
        game_data = game_response.json()["data"][0]

        votes_response = requests.get(
            GAME_VOTES_URL,
            params={"universeIds": universe_id},
            timeout=10,
        )
        votes_response.raise_for_status()
        votes_data = votes_response.json()["data"][0]

        version = self._parse_version(game_data.get("name", ""))

        return GameSnapshot(
            universe_id=universe_id,
            name=game_data.get("name", ""),
            visits=int(game_data.get("visits", 0)),
            playing=int(game_data.get("playing", 0)),
            favorites=int(game_data.get("favorites", 0)),
            up_votes=int(votes_data.get("upVotes", 0)),
            down_votes=int(votes_data.get("downVotes", 0)),
            version=version,
        )

    @staticmethod
    def _parse_version(title: str) -> Optional[str]:
        match = VERSION_PATTERN.search(title)
        if not match:
            return None
        return match.group(1)


def store_snapshot(db_path: str, snapshot: GameSnapshot) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        db_path,
        """
        INSERT INTO snapshots (
            collected_at, universe_id, name, visits, playing, favorites, up_votes, down_votes, version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now,
            snapshot.universe_id,
            snapshot.name,
            snapshot.visits,
            snapshot.playing,
            snapshot.favorites,
            snapshot.up_votes,
            snapshot.down_votes,
            snapshot.version,
        ),
    )

    if snapshot.version:
        last_version = db.fetchone(
            db_path,
            "SELECT version FROM versions ORDER BY id DESC LIMIT 1",
        )
        if not last_version or last_version["version"] != snapshot.version:
            db.execute(
                db_path,
                "INSERT INTO versions (version, detected_at) VALUES (?, ?)",
                (snapshot.version, now),
            )


def ensure_milestones(db_path: str, milestone_step: int, current_visits: int) -> None:
    row = db.fetchone(
        db_path,
        "SELECT target_visits, achieved_at FROM milestones ORDER BY target_visits DESC LIMIT 1",
    )
    if row is None:
        next_target = milestone_step
        created_at = datetime.now(timezone.utc).isoformat()
        db.execute(
            db_path,
            "INSERT INTO milestones (target_visits, created_at) VALUES (?, ?)",
            (next_target, created_at),
        )
        return

    latest_target = int(row["target_visits"])
    achieved_at = row["achieved_at"]
    if achieved_at is None and current_visits >= latest_target:
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            db_path,
            "UPDATE milestones SET achieved_at = ? WHERE target_visits = ?",
            (now, latest_target),
        )

    while current_visits >= latest_target:
        latest_target += milestone_step
        created_at = datetime.now(timezone.utc).isoformat()
        db.execute(
            db_path,
            "INSERT INTO milestones (target_visits, created_at) VALUES (?, ?)",
            (latest_target, created_at),
        )


def update_prediction_for_next_milestone(db_path: str, predicted_at: Optional[str]) -> None:
    if predicted_at is None:
        return
    db.execute(
        db_path,
        """
        UPDATE milestones
        SET predicted_at = ?
        WHERE id = (
            SELECT id FROM milestones WHERE achieved_at IS NULL ORDER BY target_visits ASC LIMIT 1
        )
        """,
        (predicted_at,),
    )
