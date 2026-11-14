"""Farm storage. SQLite by default (survives restarts); in-memory for tests."""

import sqlite3
import threading
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.farm import Farm, FarmCreate


class FarmRepository(Protocol):
    def create(self, data: FarmCreate) -> Farm: ...
    def get(self, farm_id: str) -> Farm | None: ...
    def list(self) -> list[Farm]: ...


class InMemoryFarmRepository:
    def __init__(self) -> None:
        self._farms: dict[str, Farm] = {}

    def create(self, data: FarmCreate) -> Farm:
        farm = Farm(id=uuid4().hex, **data.model_dump())
        self._farms[farm.id] = farm
        return farm

    def get(self, farm_id: str) -> Farm | None:
        return self._farms.get(farm_id)

    def list(self) -> list[Farm]:
        return list(self._farms.values())


class SqliteFarmRepository:
    """Stores each farm as JSON in one table; enough for the prototype's single-node deployment."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._lock = threading.Lock()
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS farms ("
                " id TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def create(self, data: FarmCreate) -> Farm:
        farm = Farm(id=uuid4().hex, **data.model_dump())
        with self._lock, self._connect() as db:
            db.execute("INSERT INTO farms (id, data) VALUES (?, ?)", (farm.id, farm.model_dump_json()))
        return farm

    def get(self, farm_id: str) -> Farm | None:
        with self._connect() as db:
            row = db.execute("SELECT data FROM farms WHERE id = ?", (farm_id,)).fetchone()
        return Farm.model_validate_json(row[0]) if row else None

    def list(self) -> list[Farm]:
        with self._connect() as db:
            rows = db.execute("SELECT data FROM farms ORDER BY created_at, id").fetchall()
        return [Farm.model_validate_json(r[0]) for r in rows]


@lru_cache
def get_farm_store() -> FarmRepository:
    return SqliteFarmRepository(get_settings().database_path)
