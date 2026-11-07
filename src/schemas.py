from datetime import datetime

from pydantic import BaseModel

from models import BundleFile


class Coordinate(BaseModel):
    lat: float
    lng: float


class Bounds(BaseModel):
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float


class CitySummary(BaseModel):
    slug: str
    name: str
    center: Coordinate
    bounds: Bounds
    latest_version: int


class BundleFileInfo(BaseModel):
    size: int | None
    sha256: str | None
    url: str


class VersionManifest(BaseModel):
    city: str
    version: int
    published_at: datetime | None
    bounds: Bounds
    files: dict[BundleFile, BundleFileInfo]


class PlaceResult(BaseModel):
    category: str
    id: int
    name: str | None
    name_en: str | None
    name_ar: str | None
    lat: float
    lng: float


class SearchResponse(BaseModel):
    version: int
    results: list[PlaceResult]
