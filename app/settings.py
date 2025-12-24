from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    place_id: int = 696347899
    data_refresh_seconds: int = 300
    milestone_step: int = 5_000_000
    db_path: str = "data.sqlite3"


SETTINGS = Settings()
