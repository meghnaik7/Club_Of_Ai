from fastapi import APIRouter
from app.api.endpoints import auth, events, volunteers
from app.api.v1.endpoints import documents

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(volunteers.router, prefix="/volunteers", tags=["volunteers"])
api_router.include_router(documents.router)
