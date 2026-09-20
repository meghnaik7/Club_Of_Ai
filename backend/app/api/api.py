from fastapi import APIRouter
from app.api.endpoints import (
    auth,
    events,
    volunteers,
    documents,
    ai_commands,
    announcements,
    tasks,
    teams,
    permissions,
    memory_routes,
    escalation,
    admin_org,
    users,
    feedback,
)
from app.voice.router import router as voice_router

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin_org.router, prefix="/admin", tags=["admin_org"])
api_router.include_router(feedback.router, prefix="/ai/feedback", tags=["feedback"])
api_router.include_router(ai_commands.router, prefix="/ai", tags=["ai_commands"])
api_router.include_router(voice_router, prefix="/voice", tags=["voice"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(volunteers.router, prefix="/volunteers", tags=["volunteers"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(memory_routes.router, prefix="/memory", tags=["memory"])
api_router.include_router(escalation.router, prefix="/escalations", tags=["escalations"])

