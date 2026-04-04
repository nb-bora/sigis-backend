from fastapi import APIRouter

from api.v1 import (
    audit,
    auth,
    establishments,
    exception_requests,
    health,
    missions,
    reports,
    roles,
    site_visits,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(establishments.router)
api_router.include_router(missions.router)
api_router.include_router(site_visits.router)
api_router.include_router(exception_requests.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
