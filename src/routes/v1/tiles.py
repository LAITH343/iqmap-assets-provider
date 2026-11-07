import pathlib
from typing import Annotated, Any
from urllib.parse import unquote

from fastapi import APIRouter, Header, HTTPException, Path, Request, Response, status

from models import BundleFile
from routes.dependencies import LatestBundleDep
from services import mbtiles
from services.bundles import Bundle

router = APIRouter(prefix="/cities", tags=["tiles"])

VECTOR_TILE_MEDIA_TYPE = "application/x-protobuf"
TILE_CACHE_CONTROL = "public, max-age=3600"


def _tiles_path(bundle: Bundle) -> pathlib.Path:
    path = bundle.path(BundleFile.TILES)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tiles not found.")
    return path


@router.get("/{slug}/tiles.json")
def get_tilejson(request: Request, bundle: LatestBundleDep) -> dict[str, Any]:
    metadata = mbtiles.read_metadata(_tiles_path(bundle))
    template = unquote(str(request.url_for("get_tile", slug=bundle.city.slug, z="{z}", x="{x}", y="{y}")))
    return {
        "tilejson": "3.0.0",
        "name": bundle.city.name,
        "version": str(bundle.version.version),
        "scheme": "xyz",
        "tiles": [template],
        **metadata,
    }


@router.get(
    "/{slug}/tiles/{z}/{x}/{y}.pbf",
    name="get_tile",
    responses={204: {"description": "No tile at this position"}, 304: {"description": "Not modified"}},
)
def get_tile(
    bundle: LatestBundleDep,
    z: Annotated[int, Path(ge=0, le=22)],
    x: Annotated[int, Path(ge=0)],
    y: Annotated[int, Path(ge=0)],
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    if x >= 1 << z or y >= 1 << z:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tile coordinates out of range.")

    version = bundle.version.version
    headers = {
        "etag": f'"{bundle.city.slug}-{version}-{z}-{x}-{y}"',
        "cache-control": TILE_CACHE_CONTROL,
        "x-bundle-version": str(version),
    }
    if if_none_match == headers["etag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    data = mbtiles.read_tile(_tiles_path(bundle), z, x, y)
    if data is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=headers)

    if mbtiles.is_gzipped(data):
        headers["content-encoding"] = "gzip"
    return Response(content=data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)
