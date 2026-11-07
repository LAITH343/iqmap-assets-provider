from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class BundleVersionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


class BundleFile(StrEnum):
    TILES = "tiles"
    PLACES = "places"
    GRAPH = "graph"

    @property
    def file_name(self) -> str:
        return {
            BundleFile.TILES: "tiles.mbtiles",
            BundleFile.PLACES: "places.db",
            BundleFile.GRAPH: "graph.db",
        }[self]


class City(SQLModel, table=True):
    __tablename__ = "cities"  # pyright: ignore[reportAssignmentType]

    id: int = Field(primary_key=True)
    country_id: int
    name: str
    slug: str
    center_lat: float
    center_lng: float
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float


class BundleVersion(SQLModel, table=True):
    __tablename__ = "bundle_versions"  # pyright: ignore[reportAssignmentType]

    id: int = Field(primary_key=True)
    city_id: int = Field(foreign_key="cities.id")
    version: int
    status: str
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float
    tiles_size: int | None = None
    places_size: int | None = None
    graph_size: int | None = None
    tiles_sha256: str | None = None
    places_sha256: str | None = None
    graph_sha256: str | None = None
    finished_at: datetime | None = None

    def size(self, file: BundleFile) -> int | None:
        return getattr(self, f"{file.value}_size")

    def sha256(self, file: BundleFile) -> str | None:
        return getattr(self, f"{file.value}_sha256")

    def contains(self, lat: float, lng: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lng <= lng <= self.max_lng
