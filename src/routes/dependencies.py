from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from core.config import Settings, get_settings
from core.database import get_session
from models import BundleVersion, City
from services.bundles import Bundle, bundle_directory, find_city, find_ready_version
from services.routing import RoutingEngineClient

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_city(slug: str, session: SessionDep) -> City:
    city = find_city(session, slug)
    if city is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "City not found.")
    return city


CityDep = Annotated[City, Depends(get_city)]


def _bundle(city: City, version: BundleVersion, settings: Settings) -> Bundle:
    return Bundle(city=city, version=version, directory=bundle_directory(settings.storage_root, city, version))


def get_latest_bundle(city: CityDep, session: SessionDep, settings: SettingsDep) -> Bundle:
    version = find_ready_version(session, city)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "City has no published version.")
    return _bundle(city, version, settings)


def get_bundle(version: int, city: CityDep, session: SessionDep, settings: SettingsDep) -> Bundle:
    bundle_version = find_ready_version(session, city, version)
    if bundle_version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found.")
    return _bundle(city, bundle_version, settings)


LatestBundleDep = Annotated[Bundle, Depends(get_latest_bundle)]
BundleDep = Annotated[Bundle, Depends(get_bundle)]


def get_routing_engine(request: Request) -> RoutingEngineClient:
    return request.app.state.routing_engine


RoutingEngineDep = Annotated[RoutingEngineClient, Depends(get_routing_engine)]
