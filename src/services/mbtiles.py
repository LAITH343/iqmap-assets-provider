import json
from pathlib import Path
from typing import Any

from services.sqlite import open_readonly

GZIP_MAGIC = b"\x1f\x8b"


def read_tile(path: Path, z: int, x: int, y: int) -> bytes | None:
    tms_y = (1 << z) - 1 - y
    with open_readonly(path) as conn:
        row = conn.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
            (z, x, tms_y),
        ).fetchone()
    return row[0] if row else None


def is_gzipped(data: bytes) -> bool:
    return data[:2] == GZIP_MAGIC


def read_metadata(path: Path) -> dict[str, Any]:
    with open_readonly(path) as conn:
        values = dict(conn.execute("SELECT name, value FROM metadata").fetchall())

    metadata: dict[str, Any] = {
        "format": values.get("format", "pbf"),
        "minzoom": int(values.get("minzoom", 0)),
        "maxzoom": int(values.get("maxzoom", 14)),
        "vector_layers": [],
    }
    if "bounds" in values:
        metadata["bounds"] = [float(v) for v in values["bounds"].split(",")]
    if "center" in values:
        lng, lat, zoom = values["center"].split(",")
        metadata["center"] = [float(lng), float(lat), int(zoom)]
    if "json" in values:
        metadata["vector_layers"] = json.loads(values["json"]).get("vector_layers", [])
    return metadata
