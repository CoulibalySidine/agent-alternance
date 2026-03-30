"""
deps.py — Dépendances partagées de l'API
==========================================
"""

from fastapi import HTTPException
from config import env


def get_api_key() -> str:
    """
    Récupère la clé API Anthropic.

    Utilisée comme dépendance FastAPI dans les routes
    qui appellent l'API Claude (scoring, génération).
    """
    api_key = env("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "Clé API Anthropic non configurée. "
                "Ajoute ANTHROPIC_API_KEY dans le fichier .env"
            )
        )
    return api_key
