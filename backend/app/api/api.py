from fastapi import APIRouter
from app.api.endpoints import auth, events, volunteers, documents, ai_commands, announcements, tasks, memory_routes, escalation, permissions, teams
from app.voice.router import router as voice_router

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(ai_commands.router, prefix="/ai", tags=["ai_commands"])
api_router.include_router(voice_router, prefix="/voice", tags=["voice"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(volunteers.router, prefix="/volunteers", tags=["volunteers"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(memory_routes.router, prefix="/memory", tags=["memory"])
api_router.include_router(escalation.router, prefix="/escalations", tags=["escalations"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])

