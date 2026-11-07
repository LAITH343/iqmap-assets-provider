import gzip
import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from core.config import get_settings
from core.database import get_session
from main import app
from models import BundleVersion, BundleVersionStatus, City
from routes.dependencies import get_routing_engine

TILE_BYTES = gzip.compress(b"vector-tile")


def build_tiles(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
    conn.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [
            ("format", "pbf"),
            ("minzoom", "0"),
            ("maxzoom", "14"),
            ("bounds", "44.3,33.2,44.5,33.4"),
            ("center", "44.4,33.3,7"),
            ("json", json.dumps({"vector_layers": [{"id": "transportation"}]})),
        ],
    )
    conn.execute("INSERT INTO tiles VALUES (14, 10397, 9845, ?)", (TILE_BYTES,))
    conn.commit()
    conn.close()


def build_places(path: Path) -> None:
    conn = sqlite3.connect(path)
    for table in ("amenities", "healthcare", "shops"):
        conn.execute(
            f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT, name_en TEXT, name_ar TEXT, "
            "lat REAL, lon REAL, geometry TEXT, tags TEXT)"
        )
        conn.execute(
            f"CREATE VIRTUAL TABLE {table}_fts USING fts5("
            f"name, name_en, name_ar, content='{table}', content_rowid='id')"
        )
    rows = {
        "amenities": [
            (1, "مستشفى ابن سينا", "Ibn Sina Hospital", "مستشفى ابن سينا", 33.31, 44.39),
            (2, "Central Mosque", "Central Mosque", None, 33.32, 44.40),
            (3, "Unplaced Hospital", None, None, None, None),
        ],
        "healthcare": [(1, "مستشفى ابن سينا", "Ibn Sina Hospital", "مستشفى ابن سينا", 33.31, 44.39)],
        "shops": [(1, "Hospital Pharmacy", "Hospital Pharmacy", None, 33.33, 44.41)],
    }
    for table, values in rows.items():
        conn.executemany(f"INSERT INTO {table} (id, name, name_en, name_ar, lat, lon) VALUES (?,?,?,?,?,?)", values)
        conn.execute(
            f"INSERT INTO {table}_fts(rowid, name, name_en, name_ar) SELECT id, name, name_en, name_ar FROM {table}"
        )
    conn.commit()
    conn.close()


class FakeRoutingEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error: Exception | None = None

    async def route(self, graph_path, profile, origin, destination) -> dict[str, Any]:
        self.calls.append({"graph_path": graph_path, "profile": profile, "from": origin, "to": destination})
        if self.error:
            raise self.error
        return {"distance_m": 1200.0, "duration_s": 300.0, "points": [list(origin), list(destination)], "steps": []}


@pytest.fixture
def storage(tmp_path: Path) -> Path:
    directory = tmp_path / "bundles" / "baghdad" / "2"
    directory.mkdir(parents=True)
    build_tiles(directory / "tiles.mbtiles")
    build_places(directory / "places.db")
    (directory / "graph.db").write_bytes(b"0123456789" * 10)
    return tmp_path


def make_version(id: int, city_id: int, version: int, status: BundleVersionStatus) -> BundleVersion:
    return BundleVersion(
        id=id,
        city_id=city_id,
        version=version,
        status=status,
        min_lat=33.2,
        min_lng=44.3,
        max_lat=33.4,
        max_lng=44.5,
    )


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        city = City(
            id=1,
            country_id=1,
            name="Baghdad",
            slug="baghdad",
            center_lat=33.3,
            center_lng=44.4,
            min_lat=33.2,
            min_lng=44.3,
            max_lat=33.4,
            max_lng=44.5,
        )
        empty = City(
            id=2,
            country_id=1,
            name="Basra",
            slug="basra",
            center_lat=30.5,
            center_lng=47.8,
            min_lat=30.4,
            min_lng=47.7,
            max_lat=30.6,
            max_lng=47.9,
        )
        ready = make_version(1, 1, 1, BundleVersionStatus.READY)
        latest = make_version(2, 1, 2, BundleVersionStatus.READY)
        latest.tiles_size, latest.places_size, latest.graph_size = 10, 20, 100
        latest.tiles_sha256, latest.places_sha256, latest.graph_sha256 = "a" * 64, "b" * 64, "c" * 64
        session.add_all(
            [
                city,
                empty,
                ready,
                latest,
                make_version(3, 1, 3, BundleVersionStatus.RUNNING),
                make_version(4, 2, 1, BundleVersionStatus.FAILED),
            ]
        )
        session.commit()
        yield session


@pytest.fixture
def routing_engine() -> FakeRoutingEngine:
    return FakeRoutingEngine()


@pytest.fixture
def client(
    storage: Path,
    session: Session,
    routing_engine: FakeRoutingEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("STORAGE_ROOT", str(storage))
    get_settings.cache_clear()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_routing_engine] = lambda: routing_engine
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()
