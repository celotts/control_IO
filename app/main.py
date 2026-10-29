from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.config import settings
from app.core.logging import setup_logging
from app.routers import health, planillas, reportes

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="API REST para digitalización de Lista de Asistencia SFSD0001",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload and storage directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(planillas.router, prefix=f"{settings.API_V1_PREFIX}/planillas", tags=["Planillas"])
app.include_router(reportes.router, prefix=f"{settings.API_V1_PREFIX}/reportes", tags=["Reportes"])
