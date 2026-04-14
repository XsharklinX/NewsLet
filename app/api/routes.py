# routes.py — aggregator only
from fastapi import APIRouter, Depends

from app.services.auth import require_auth

from app.api.routers.articles import router as articles_router
from app.api.routers.sources import router as sources_router
from app.api.routers.analytics import router as analytics_router
from app.api.routers.operations import router as operations_router
from app.api.routers.config import router as config_router
from app.api.routers.auth import public_router as auth_public_router

public_router = APIRouter(prefix="/api/v1")
router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_auth)],
)

# Each sub-router already carries its own /api/v1 prefix and auth dependency.
# Include them all at the application level. The `router` and `public_router`
# objects above are kept for backward compatibility with any code that imports
# them from this module, but the actual endpoints live in the sub-routers.

# Convenience lists for main.py (or wherever the FastAPI app is assembled):
#
#   for r in routes.protected_routers + routes.public_routers:
#       app.include_router(r)

protected_routers = [
    articles_router,
    sources_router,
    analytics_router,
    operations_router,
    config_router,
]

public_routers = [
    auth_public_router,
]
