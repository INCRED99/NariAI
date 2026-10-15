import sys
import os
import json
import uvicorn
import firebase_admin

# Ensure the parent directory and current directory are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for p in [parent_dir, current_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from firebase_admin import credentials
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import FIREBASE_SERVICE_ACCOUNT_PATH

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

    if firebase_json:
        try:
            # Check if base64 encoded
            raw_content = firebase_json.strip()
            if not raw_content.startswith("{"):
                try:
                    import base64
                    decoded = base64.b64decode(raw_content).decode("utf-8")
                    if decoded.strip().startswith("{"):
                        raw_content = decoded
                except Exception:
                    pass
            firebase_dict = json.loads(raw_content)
            cred = credentials.Certificate(firebase_dict)
            firebase_admin.initialize_app(cred)
            print("INFO: Firebase Admin successfully initialized from FIREBASE_SERVICE_ACCOUNT env var.")
        except Exception as e:
            print(f"WARNING: Error initializing Firebase Admin from FIREBASE_SERVICE_ACCOUNT env var: {e}")
    elif os.path.exists(FIREBASE_SERVICE_ACCOUNT_PATH):
        try:
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
            print("INFO: Firebase Admin successfully initialized from local serviceaccount.json.")
        except Exception as e:
            print(f"WARNING: Error initializing Firebase Admin from serviceaccount.json: {e}")
    else:
        print("WARNING: Neither FIREBASE_SERVICE_ACCOUNT env var nor backend/serviceaccount.json found. Firebase authentication endpoints will require valid credentials.")

from backend.routes import risk_assessment, sos, routes, nearby, profile, voice, chat, rag, auth
from backend.database import seed_default_user
from backend.services.memory_service import seed_default_memories
from backend.services.qdrant_service import initialize_qdrant
app = FastAPI(
    title="Nari AI Safety Assistant Backend",
    description="Production-grade API endpoints for Women's Safety Assistant, featuring Gemini AI threat modeling, Qdrant RAG, and Mem0 Safety Memory.",
    version="1.0.0"
)

# Enable CORS for frontend requests (supports local dev and Vercel deployments)
cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nari-ai-sandy.vercel.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files to serve emergency audio recordings
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(os.path.join(static_dir, "audio"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Register route modules (support both /api prefix and root prefix)
for r in [auth.router, risk_assessment.router, sos.router, routes.router, nearby.router, profile.router, voice.router, chat.router, rag.router]:
    app.include_router(r, prefix="/api")
    app.include_router(r)

# Alias /routes for frontend route calls
app.include_router(routes.router, prefix="/api/routes")
app.include_router(routes.router, prefix="/routes")

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
