from fastapi import APIRouter
from app.api.endpoints import auth, events, volunteers, documents, ai_commands, announcements
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(ai_commands.router, prefix="/ai", tags=["ai_commands"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(volunteers.router, prefix="/volunteers", tags=["volunteers"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
