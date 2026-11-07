from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func
from sqlmodel import Session, col, select

from models import BundleFile, BundleVersion, BundleVersionStatus, City


@dataclass(frozen=True)
class Bundle:
    city: City
    version: BundleVersion
    directory: Path

    def path(self, file: BundleFile) -> Path:
        return self.directory / file.file_name


def bundle_directory(storage_root: Path, city: City, version: BundleVersion) -> Path:
    return storage_root / "bundles" / city.slug / str(version.version)


def find_city(session: Session, slug: str) -> City | None:
    return session.exec(select(City).where(City.slug == slug)).first()


def find_ready_version(session: Session, city: City, version: int | None = None) -> BundleVersion | None:
    statement = select(BundleVersion).where(
        BundleVersion.city_id == city.id,
        BundleVersion.status == BundleVersionStatus.READY,
    )
    if version is None:
        statement = statement.order_by(col(BundleVersion.version).desc()).limit(1)
    else:
        statement = statement.where(BundleVersion.version == version)
    return session.exec(statement).first()


def list_published_cities(session: Session) -> list[tuple[City, int]]:
    latest = (
        select(BundleVersion.city_id, func.max(BundleVersion.version).label("version"))
        .where(BundleVersion.status == BundleVersionStatus.READY)
        .group_by(col(BundleVersion.city_id))
        .subquery()
    )
    statement = select(City, latest.c.version).join(latest, latest.c.city_id == City.id).order_by(col(City.name))
    return [(city, version) for city, version in session.exec(statement).all()]
