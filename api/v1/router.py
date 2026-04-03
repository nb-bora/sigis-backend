from fastapi import APIRouter

from api.v1 import establishments, exception_requests, health, missions, site_visits

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(establishments.router)
api_router.include_router(missions.router)
api_router.include_router(site_visits.router)
api_router.include_router(exception_requests.router)
