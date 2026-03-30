"""
routes/profil.py — Endpoints du module Profil
===============================================

POST /profil/upload    → Upload un CV, Claude génère le profil
GET  /profil           → Voir le profil actuel
PUT  /profil           → Modifier le profil manuellement
DELETE /profil          → Supprimer le profil (reset)
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from profil.extracteur import extraire_texte
from profil.generateur_profil import (
    generer_profil, sauvegarder_profil, charger_profil, PROFIL_PATH,
)
from api.deps import get_api_key
from api.tasks import task_manager
from api.schemas import TaskResponse, TaskStatus
from logger import get_logger

log = get_logger("api.profil")

router = APIRouter(prefix="/profil", tags=["Profil"])

# Dossier temporaire pour stocker le CV uploadé
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"


class ProfilResponse(BaseModel):
    existe: bool
    contenu: Optional[str] = None


class ProfilUpdateRequest(BaseModel):
    contenu: str


# ============================================================
# POST /profil/upload — Upload CV et génération du profil
# ============================================================

@router.post("/upload", response_model=TaskResponse)
async def upload_cv(
    cv: UploadFile = File(..., description="CV au format PDF, Word ou TXT"),
    metier: str = Form(default="", description="Type de poste recherché (ex: développeur Python)"),
    ville: str = Form(default="", description="Zone géographique (ex: Paris, Lyon)"),
    api_key: str = Depends(get_api_key),
):
    """
    Upload un CV et génère automatiquement le profil.

    1. Lit le fichier (PDF, Word, TXT)
    2. Extrait le texte
    3. Envoie à Claude pour analyse
    4. Sauvegarde le profil.yaml

    L'opération est synchrone car elle prend ~5-10s (un seul appel Claude).
    """
    # Vérifier l'extension
    nom = cv.filename or "cv.pdf"
    suffix = Path(nom).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt", ".md"):
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : {suffix}. Acceptés : .pdf, .docx, .txt"
        )

    # Sauvegarder le fichier temporairement
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    chemin_temp = UPLOAD_DIR / f"cv_upload{suffix}"

    contenu = await cv.read()
    chemin_temp.write_bytes(contenu)
    log.info(f"CV uploadé : {nom} ({len(contenu)} octets)")

    try:
        # Extraire le texte
        texte_cv = extraire_texte(chemin_temp)

        if len(texte_cv.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Le CV semble vide ou illisible. Essaie un autre format."
            )

        # Générer le profil via Claude
        yaml_content = generer_profil(
            texte_cv=texte_cv,
            metier=metier,
            ville=ville,
            api_key=api_key,
        )

        # Sauvegarder
        sauvegarder_profil(yaml_content)

        log.info(f"Profil généré avec succès depuis {nom}")

        return TaskResponse(
            task_id="profil_done",
            status=TaskStatus.DONE,
            result={
                "message": "Profil généré avec succès",
                "source": nom,
                "metier": metier or "(déduit du CV)",
                "ville": ville or "(déduit du CV)",
                "taille_profil": len(yaml_content),
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Erreur génération profil : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur : {e}")
    finally:
        # Nettoyer le fichier temporaire
        if chemin_temp.exists():
            chemin_temp.unlink()


# ============================================================
# GET /profil — Voir le profil actuel
# ============================================================

@router.get("", response_model=ProfilResponse)
def voir_profil():
    """Retourne le profil actuel (contenu YAML brut)."""
    contenu = charger_profil()
    return ProfilResponse(
        existe=contenu is not None,
        contenu=contenu,
    )


# ============================================================
# PUT /profil — Modifier le profil
# ============================================================

@router.put("")
def modifier_profil(body: ProfilUpdateRequest):
    """
    Remplace le profil par le contenu fourni.
    Permet à l'utilisateur de corriger le profil généré.
    """
    if not body.contenu.strip():
        raise HTTPException(status_code=400, detail="Le profil ne peut pas être vide")

    sauvegarder_profil(body.contenu)
    log.info("Profil mis à jour manuellement")

    return {"message": "Profil mis à jour", "taille": len(body.contenu)}


# ============================================================
# DELETE /profil — Supprimer le profil
# ============================================================

@router.delete("")
def supprimer_profil():
    """Supprime le profil actuel (reset)."""
    if PROFIL_PATH.exists():
        backup = PROFIL_PATH.with_suffix(".yaml.bak")
        shutil.copy2(PROFIL_PATH, backup)
        PROFIL_PATH.unlink()
        log.info("Profil supprimé (backup créé)")
        return {"message": "Profil supprimé", "backup": str(backup)}
    else:
        raise HTTPException(status_code=404, detail="Aucun profil à supprimer")
