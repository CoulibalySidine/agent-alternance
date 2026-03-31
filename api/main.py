"""
main.py — Point d'entrée de l'API FastAPI
==========================================

Toutes les routes sont sous /api pour éviter les conflits
avec les routes frontend React (/suivi, /offres, etc.)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from api.routes import sourcing, qualification, candidature, suivi
from api.routes import profil as profil_routes
from logger import get_logger

log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Agent Alternance API démarrée")
    log.info("📖 Documentation : http://localhost:8000/docs")
    yield
    log.info("🛑 Agent Alternance API arrêtée")


app = FastAPI(
    title="Agent Alternance API",
    description=(
        "API pour automatiser la recherche d'alternance : "
        "upload CV, collecte d'offres, scoring IA, génération de candidatures, suivi."
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Regrouper tous les routers sous /api
api_router = APIRouter(prefix="/api")
api_router.include_router(profil_routes.router)
api_router.include_router(sourcing.router)
api_router.include_router(qualification.router)
api_router.include_router(candidature.router)
api_router.include_router(suivi.router)

app.include_router(api_router)


@app.get("/", tags=["Système"])
def racine():
    return {
        "nom": "Agent Alternance API",
        "version": "1.1.0",
        "documentation": "/docs",
        "flux": "1. Upload CV → 2. Scrape → 3. Score → 4. Générer dossier → 5. Suivi",
    }


@app.get("/api/health", tags=["Système"])
def health():
    from pathlib import Path
    import os

    profil_path = Path(__file__).parent.parent / "qualification" / "profil.yaml"
    offres_path = Path(__file__).parent.parent / "sourcing" / "offres.json"
    suivi_path = Path(__file__).parent.parent / "suivi" / "suivi.json"

    checks = {
        "api": "ok",
        "profil.yaml": "ok" if profil_path.exists() else "manquant",
        "offres.json": "ok" if offres_path.exists() else "manquant",
        "suivi.json": "ok" if suivi_path.exists() else "manquant",
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    checks["api_key"] = "configurée" if api_key else "manquante"

    status_global = "ok" if checks["api"] == "ok" and checks["api_key"] == "configurée" else "dégradé"
    return {"status": status_global, "checks": checks}
