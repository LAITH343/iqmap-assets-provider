from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from models import BundleFile
from routes.dependencies import LatestBundleDep
from schemas import PlaceResult, SearchResponse
from services import places

router = APIRouter(prefix="/cities", tags=["search"])


@router.get("/{slug}/search")
def search_places(
    bundle: LatestBundleDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    category: str | None = None,
) -> SearchResponse:
    path = bundle.path(BundleFile.PLACES)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Places not found.")

    if category is not None and category not in places.categories(path):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown category '{category}'.")

    results = places.search(path, q, limit, category)
    return SearchResponse(
        version=bundle.version.version,
        results=[PlaceResult(**asdict(place)) for place in results],
    )
