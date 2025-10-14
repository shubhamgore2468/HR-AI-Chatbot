from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import init_db
from app.api.v1.api import api_router
from app.core.logger import log
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.on_event("startup")
def startup_event():
    init_db()
    log.info("Database initialized")

@app.get("/")
def read_root():
    return {
        "message" : "HR agent API",
        "version" : "1.0.0",
        "endpoints" : ["/chat", "/sessions", "/sessions/{session_id}"]
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}
