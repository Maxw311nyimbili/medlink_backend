from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.firebase import initialize_firebase  # ← UNCOMMENTED
from app.api import auth, forum, landing, chat, media  # ← Add media

# Initialize Firebase
initialize_firebase()  # ← UNCOMMENTED - will enable after setup

app = FastAPI(
    title="MedLink API",
    description="Medical information platform backend",
    version="1.0.0"
)

# CORS
origins = settings.ALLOWED_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(forum.router)
app.include_router(landing.router)
app.include_router(chat.router)
app.include_router(media.router)  # ← Add

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "message": "MedLink API v1.0.0",
        "endpoints": {
            "auth": "/auth",
            "forum": "/forum",
            "landing": "/landing",
            "chat": "/chat",
            "media": "/media",
            "docs": "/docs"
        }
    }