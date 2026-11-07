from fastapi import APIRouter

from routes import health
from routes.v1.router import v1_router

router = APIRouter()
router.include_router(health.router)
router.include_router(v1_router)
