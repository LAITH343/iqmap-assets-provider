from fastapi import APIRouter

from routes.v1 import cities, routing, search, tiles

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(cities.router)
v1_router.include_router(tiles.router)
v1_router.include_router(search.router)
v1_router.include_router(routing.router)
