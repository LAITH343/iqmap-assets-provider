import math
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from models import BundleFile
from routes.dependencies import LatestBundleDep, RoutingEngineDep
from services.bundles import Bundle
from services.routing import RouteNotFoundError, RouteProfile, RoutingEngineError, RoutingEngineUnavailableError

router = APIRouter(prefix="/cities", tags=["routing"])

COORDINATE_PATTERN = r"^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$"


def _parse_coordinate(value: str, name: str, bundle: Bundle) -> tuple[float, float]:
    lat, lng = (float(part) for part in value.split(","))
    if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"'{name}' is not a valid coordinate.")
    if not bundle.version.contains(lat, lng):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"'{name}' is outside the {bundle.city.name} coverage area.",
        )
    return lat, lng


def get_graph_path(bundle: LatestBundleDep) -> Path:
    path = bundle.path(BundleFile.GRAPH)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Graph not found.")
    return path


@router.get("/{slug}/route")
async def get_route(
    response: Response,
    bundle: LatestBundleDep,
    graph_path: Annotated[Path, Depends(get_graph_path)],
    engine: RoutingEngineDep,
    origin: Annotated[str, Query(alias="from", pattern=COORDINATE_PATTERN, description="lat,lng")],
    destination: Annotated[str, Query(alias="to", pattern=COORDINATE_PATTERN, description="lat,lng")],
    profile: RouteProfile,
) -> dict[str, Any]:
    start = _parse_coordinate(origin, "from", bundle)
    end = _parse_coordinate(destination, "to", bundle)

    try:
        route = await engine.route(graph_path, profile, start, end)
    except RouteNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No route found between the given points.") from None
    except RoutingEngineUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Routing engine is unavailable.") from None
    except RoutingEngineError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Routing engine failed to compute a route.") from None

    response.headers["x-bundle-version"] = str(bundle.version.version)
    return route
