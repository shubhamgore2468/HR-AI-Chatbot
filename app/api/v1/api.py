from fastapi import APIRouter
from .chat import router as chatbot_router
# from .session import router as session_router

api_router = APIRouter()

# api_router.include_router(session_router, prefix="/session", tags=["auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])

@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    print("Health check endpoint called")
    return {"status": "healthy", "version": "1.0.0"}