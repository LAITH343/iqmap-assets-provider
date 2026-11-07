import sqlite3
from contextlib import closing
from pathlib import Path


def open_readonly(path: Path) -> closing[sqlite3.Connection]:
    return closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True))
