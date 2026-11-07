from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from models import BundleFile
from routes.dependencies import BundleDep, LatestBundleDep, SessionDep
from schemas import Bounds, BundleFileInfo, CitySummary, Coordinate, VersionManifest
from services.bundles import Bundle, list_published_cities

router = APIRouter(prefix="/cities", tags=["cities"])

SQLITE_MEDIA_TYPE = "application/vnd.sqlite3"


@router.get("")
def list_cities(session: SessionDep) -> list[CitySummary]:
    return [
        CitySummary(
            slug=city.slug,
            name=city.name,
            center=Coordinate(lat=city.center_lat, lng=city.center_lng),
            bounds=Bounds(
                min_lat=city.min_lat,
                min_lng=city.min_lng,
                max_lat=city.max_lat,
                max_lng=city.max_lng,
            ),
            latest_version=version,
        )
        for city, version in list_published_cities(session)
    ]


def _manifest(request: Request, bundle: Bundle) -> VersionManifest:
    version = bundle.version
    return VersionManifest(
        city=bundle.city.slug,
        version=version.version,
        published_at=version.finished_at,
        bounds=Bounds(
            min_lat=version.min_lat,
            min_lng=version.min_lng,
            max_lat=version.max_lat,
            max_lng=version.max_lng,
        ),
        files={
            file: BundleFileInfo(
                size=version.size(file),
                sha256=version.sha256(file),
                url=str(
                    request.url_for(
                        "download_bundle_file",
                        slug=bundle.city.slug,
                        version=str(version.version),
                        file=file.value,
                    )
                ),
            )
            for file in BundleFile
        },
    )


@router.get("/{slug}/versions/latest")
def get_latest_version(request: Request, bundle: LatestBundleDep) -> VersionManifest:
    return _manifest(request, bundle)


@router.get("/{slug}/versions/{version}")
def get_version(request: Request, bundle: BundleDep) -> VersionManifest:
    return _manifest(request, bundle)


@router.api_route(
    "/{slug}/versions/{version}/files/{file}",
    methods=["GET", "HEAD"],
    name="download_bundle_file",
    response_class=FileResponse,
)
def download_bundle_file(bundle: BundleDep, file: BundleFile) -> FileResponse:
    path = bundle.path(file)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.")

    headers = {"cache-control": "public, max-age=31536000, immutable"}
    checksum = bundle.version.sha256(file)
    if checksum:
        headers["etag"] = f'"{checksum}"'

    return FileResponse(
        path,
        media_type=SQLITE_MEDIA_TYPE,
        filename=f"{bundle.city.slug}-v{bundle.version.version}-{file.file_name}",
        headers=headers,
    )
