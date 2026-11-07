import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from services.sqlite import open_readonly

FTS_SUFFIX = "_fts"
TERM_PATTERN = re.compile(r"\w+")


@dataclass(frozen=True)
class Place:
    category: str
    id: int
    name: str | None
    name_en: str | None
    name_ar: str | None
    lat: float
    lng: float


def build_match_query(query: str) -> str | None:
    terms = TERM_PATTERN.findall(query)
    if not terms:
        return None
    return " ".join(f'"{term}"*' for term in terms)


def list_categories(conn: sqlite3.Connection) -> list[str]:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    return sorted(
        name.removesuffix(FTS_SUFFIX)
        for name in tables
        if name.endswith(FTS_SUFFIX)
        and name.removesuffix(FTS_SUFFIX) in tables
        and name.removesuffix(FTS_SUFFIX).isidentifier()
    )


def categories(path: Path) -> list[str]:
    with open_readonly(path) as conn:
        return list_categories(conn)


def search(path: Path, query: str, limit: int, category: str | None = None) -> list[Place]:
    match = build_match_query(query)
    if match is None:
        return []

    with open_readonly(path) as conn:
        available = list_categories(conn)
        selected = [category] if category else available
        selected = [name for name in selected if name in available]
        if not selected:
            return []

        selects = [
            f"""SELECT '{name}', t.id, t.name, t.name_en, t.name_ar, t.lat, t.lon, bm25("{name}_fts")
            FROM "{name}_fts" JOIN "{name}" t ON t.id = "{name}_fts".rowid
            WHERE "{name}_fts" MATCH :match AND t.lat IS NOT NULL AND t.lon IS NOT NULL"""
            for name in selected
        ]
        sql = f"SELECT * FROM ({' UNION ALL '.join(selects)}) ORDER BY 8 LIMIT :fetch"
        rows = conn.execute(sql, {"match": match, "fetch": limit * 3}).fetchall()

    places: list[Place] = []
    seen: set[tuple[str | None, float, float]] = set()
    for category_name, place_id, name, name_en, name_ar, lat, lng, _ in rows:
        key = (name, round(lat, 5), round(lng, 5))
        if key in seen:
            continue
        seen.add(key)
        places.append(Place(category_name, place_id, name, name_en, name_ar, lat, lng))
        if len(places) == limit:
            break
    return places
