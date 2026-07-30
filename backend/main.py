import json
import os
import uvicorn
import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import FIREBASE_SERVICE_ACCOUNT_PATH

# Initialize Firebase Admin SDK
# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

    if not firebase_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT environment variable is not set.")

    firebase_dict = json.loads(firebase_json)

    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred)

from backend.routes import risk_assessment, sos, routes, nearby, profile, voice, chat, rag, auth
from backend.database import seed_default_user
from backend.services.memory_service import seed_default_memories
from backend.services.qdrant_service import initialize_qdrant
app = FastAPI(
    title="Nari AI Safety Assistant Backend",
    description="Production-grade API endpoints for Women's Safety Assistant, featuring Gemini AI threat modeling, Qdrant RAG, and Mem0 Safety Memory.",
    version="1.0.0"
)

# Enable CORS for frontend Streamlit requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files to serve emergency audio recordings
from fastapi.staticfiles import StaticFiles
import os

os.makedirs("backend/static/audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Register route modules
app.include_router(auth.router, prefix="/api")
app.include_router(risk_assessment.router, prefix="/api")
app.include_router(sos.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(nearby.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(rag.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    """Trigger DB seeds and initialize AI Vector Indexes on startup."""
    seed_default_user()
    seed_default_memories()
    initialize_qdrant()

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "Nari Women's Safety Core API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
