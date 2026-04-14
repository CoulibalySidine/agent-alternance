"""
routes/profil.py — Endpoints du module Profil (v2)
====================================================

POST /profil/upload       → Upload un CV, Claude génère le profil
GET  /profil              → Voir le profil actuel (YAML brut)
GET  /profil/parsed       → Voir le profil en JSON structuré (pour l'éditeur visuel)
PUT  /profil              → Modifier le profil (YAML brut)
PUT  /profil/structured   → Modifier le profil (JSON structuré → converti en YAML)
DELETE /profil             → Supprimer le profil (reset)
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

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


class ProfilStructuredUpdate(BaseModel):
    profil: dict


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
    """
    nom = cv.filename or "cv.pdf"
    suffix = Path(nom).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt", ".md"):
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : {suffix}. Acceptés : .pdf, .docx, .txt"
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    chemin_temp = UPLOAD_DIR / f"cv_upload{suffix}"

    contenu = await cv.read()
    chemin_temp.write_bytes(contenu)
    log.info(f"CV uploadé : {nom} ({len(contenu)} octets)")

    try:
        texte_cv = extraire_texte(chemin_temp)

        if len(texte_cv.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Le CV semble vide ou illisible. Essaie un autre format."
            )

        yaml_content = generer_profil(
            texte_cv=texte_cv,
            metier=metier,
            ville=ville,
            api_key=api_key,
        )

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
        if chemin_temp.exists():
            chemin_temp.unlink()


# ============================================================
# GET /profil — Voir le profil actuel (YAML brut)
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
# GET /profil/parsed — Voir le profil en JSON structuré
# ============================================================

@router.get("/parsed")
def voir_profil_parsed():
    """
    Retourne le profil parsé en JSON structuré.
    
    Utilisé par l'éditeur visuel du frontend pour afficher
    le profil sous forme de formulaire au lieu de YAML brut.
    """
    contenu = charger_profil()
    if contenu is None:
        return {"existe": False, "profil": None}

    if not HAS_YAML:
        raise HTTPException(
            status_code=500,
            detail="PyYAML n'est pas installé. pip install pyyaml"
        )

    try:
        profil_dict = yaml.safe_load(contenu) or {}
    except yaml.YAMLError as e:
        log.error(f"Erreur parsing YAML : {e}")
        # Si le YAML est invalide, on renvoie quand même le brut
        return {"existe": True, "profil": None, "erreur": str(e), "brut": contenu}

    # Normaliser la structure pour que le frontend ait des valeurs cohérentes
    profil_normalise = _normaliser_profil(profil_dict)

    return {"existe": True, "profil": profil_normalise}


# ============================================================
# PUT /profil — Modifier le profil (YAML brut)
# ============================================================

@router.put("")
def modifier_profil(body: ProfilUpdateRequest):
    """Remplace le profil par le contenu YAML fourni."""
    if not body.contenu.strip():
        raise HTTPException(status_code=400, detail="Le profil ne peut pas être vide")

    sauvegarder_profil(body.contenu)
    log.info("Profil mis à jour manuellement (YAML brut)")
    return {"message": "Profil mis à jour", "taille": len(body.contenu)}


# ============================================================
# PUT /profil/structured — Modifier le profil (JSON → YAML)
# ============================================================

@router.put("/structured")
def modifier_profil_structured(body: ProfilStructuredUpdate):
    """
    Reçoit le profil en JSON structuré depuis l'éditeur visuel,
    le convertit en YAML propre, et le sauvegarde.
    """
    if not HAS_YAML:
        raise HTTPException(
            status_code=500,
            detail="PyYAML n'est pas installé. pip install pyyaml"
        )

    profil = body.profil
    if not profil:
        raise HTTPException(status_code=400, detail="Le profil ne peut pas être vide")

    # Nettoyer les champs vides avant de sauvegarder
    profil_propre = _nettoyer_profil(profil)

    try:
        yaml_content = yaml.dump(
            profil_propre,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Erreur de conversion : {e}")

    sauvegarder_profil(yaml_content)
    log.info("Profil mis à jour via l'éditeur visuel")
    return {"message": "Profil mis à jour", "taille": len(yaml_content)}


# ============================================================
# DELETE /profil — Supprimer le profil
# ============================================================

@router.delete("")
def supprimer_profil():
    """Supprime le profil actuel (reset)."""
    if not PROFIL_PATH.exists():
        raise HTTPException(status_code=404, detail="Aucun profil à supprimer")

    backup = PROFIL_PATH.with_suffix(".yaml.bak")
    PROFIL_PATH.rename(backup)
    log.info("Profil supprimé (backup conservé)")

    return {"message": "Profil supprimé", "backup": str(backup.name)}


# ============================================================
# Helpers — normalisation et nettoyage
# ============================================================

def _normaliser_profil(profil: dict) -> dict:
    """
    Normalise la structure du profil pour que le frontend
    ait toujours les mêmes clés, même si certaines sont absentes du YAML.
    
    Les champs manquants sont initialisés à des valeurs vides
    (string vide, liste vide, dict vide) plutôt que None.
    """
    return {
        # Identité
        "nom": profil.get("nom", ""),
        "email": profil.get("email", ""),
        "telephone": profil.get("telephone", ""),
        "localisation": profil.get("localisation", ""),
        "linkedin": profil.get("linkedin", ""),
        "github": profil.get("github", ""),
        "portfolio": profil.get("portfolio", ""),
        "titre": profil.get("titre", ""),

        # Listes structurées
        "formation": _normaliser_liste(profil.get("formation", []), {
            "diplome": "", "etablissement": "", "periode": "", "details": ""
        }),
        "experience": _normaliser_liste_experience(profil.get("experience", [])),
        "projets": _normaliser_liste(profil.get("projets", []), {
            "titre": "", "technologies": "", "description": ""
        }),
        "langues": _normaliser_liste(profil.get("langues", []), {
            "langue": "", "niveau": ""
        }),

        # Compétences (structure spéciale)
        "competences": _normaliser_competences(profil.get("competences", {})),

        # Listes simples
        "interets": _as_string_list(profil.get("interets", [])),
        "points_forts": _as_string_list(profil.get("points_forts", [])),

        # Recherche
        "recherche": {
            "type": _deep_get(profil, "recherche", "type", default=""),
            "rythme": _deep_get(profil, "recherche", "rythme", default=""),
            "duree": _deep_get(profil, "recherche", "duree", default=""),
            "domaines": _as_string_list(_deep_get(profil, "recherche", "domaines", default=[])),
            "localisation": _deep_get(profil, "recherche", "localisation", default=""),
        },
    }


def _normaliser_liste(items, template: dict) -> list:
    """Normalise une liste de dicts en s'assurant que chaque item a toutes les clés."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, dict):
            normalized = {k: item.get(k, v) for k, v in template.items()}
            # Convertir None en string vide
            normalized = {k: (v if v is not None else "") for k, v in normalized.items()}
            result.append(normalized)
        elif isinstance(item, str):
            # Si c'est juste un string, le mettre dans la première clé
            entry = dict(template)
            first_key = list(template.keys())[0]
            entry[first_key] = item
            result.append(entry)
    return result


def _normaliser_liste_experience(items) -> list:
    """Normalise les expériences (missions peut être une liste)."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append({
                "poste": item.get("poste", ""),
                "entreprise": item.get("entreprise", ""),
                "periode": item.get("periode", ""),
                "missions": _as_string_list(item.get("missions", [])),
            })
    return result


def _normaliser_competences(comp) -> dict:
    """Normalise le bloc compétences."""
    if not isinstance(comp, dict):
        return {
            "langages": [], "frameworks": [], "bases_de_donnees": [],
            "outils": [], "methodes": [],
        }

    def extract_names(items):
        """Extrait les noms depuis une liste de strings ou de dicts {nom, niveau}."""
        if not isinstance(items, list):
            return []
        result = []
        for item in items:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and "nom" in item:
                result.append(item["nom"])
        return result

    return {
        "langages": extract_names(comp.get("langages", [])),
        "frameworks": extract_names(comp.get("frameworks", [])),
        "bases_de_donnees": extract_names(comp.get("bases_de_donnees", [])),
        "outils": extract_names(comp.get("outils", [])),
        "methodes": extract_names(comp.get("methodes", [])),
    }


def _as_string_list(items) -> list:
    """Convertit en liste de strings."""
    if not isinstance(items, list):
        return []
    return [str(x) for x in items if x]


def _deep_get(d: dict, *keys, default=""):
    """Accès profond dans un dict imbriqué."""
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d if d is not None else default


def _nettoyer_profil(profil: dict) -> dict:
    """
    Supprime les champs vides du profil avant de sauvegarder en YAML.
    Un profil propre = pas de clés avec des valeurs vides.
    """
    propre = {}

    # Champs simples
    for cle in ["nom", "email", "telephone", "localisation", "linkedin",
                "github", "portfolio", "titre"]:
        val = profil.get(cle, "")
        if val and str(val).strip():
            propre[cle] = str(val).strip()

    # Formation
    formations = profil.get("formation", [])
    if formations:
        formations_propres = []
        for f in formations:
            if isinstance(f, dict) and f.get("diplome", "").strip():
                entry = {k: v for k, v in f.items() if v and str(v).strip()}
                if entry:
                    formations_propres.append(entry)
        if formations_propres:
            propre["formation"] = formations_propres

    # Expériences
    experiences = profil.get("experience", [])
    if experiences:
        exp_propres = []
        for e in experiences:
            if isinstance(e, dict) and e.get("poste", "").strip():
                entry = {}
                for k in ["poste", "entreprise", "periode"]:
                    if e.get(k, "").strip():
                        entry[k] = e[k].strip()
                missions = [m for m in e.get("missions", []) if m and str(m).strip()]
                if missions:
                    entry["missions"] = missions
                if entry:
                    exp_propres.append(entry)
        if exp_propres:
            propre["experience"] = exp_propres

    # Compétences
    comp = profil.get("competences", {})
    if isinstance(comp, dict):
        comp_propre = {}
        for cat in ["langages", "frameworks", "bases_de_donnees", "outils", "methodes"]:
            items = [x for x in comp.get(cat, []) if x and str(x).strip()]
            if items:
                comp_propre[cat] = items
        if comp_propre:
            propre["competences"] = comp_propre

    # Projets
    projets = profil.get("projets", [])
    if projets:
        projets_propres = []
        for p in projets:
            if isinstance(p, dict) and p.get("titre", "").strip():
                entry = {k: v for k, v in p.items() if v and str(v).strip()}
                if entry:
                    projets_propres.append(entry)
        if projets_propres:
            propre["projets"] = projets_propres

    # Langues
    langues = profil.get("langues", [])
    if langues:
        langues_propres = []
        for l in langues:
            if isinstance(l, dict) and l.get("langue", "").strip():
                entry = {k: v for k, v in l.items() if v and str(v).strip()}
                if entry:
                    langues_propres.append(entry)
        if langues_propres:
            propre["langues"] = langues_propres

    # Listes simples
    for cle in ["interets", "points_forts"]:
        items = [str(x).strip() for x in profil.get(cle, []) if x and str(x).strip()]
        if items:
            propre[cle] = items

    # Recherche
    recherche = profil.get("recherche", {})
    if isinstance(recherche, dict):
        rech_propre = {}
        for cle in ["type", "rythme", "duree", "localisation"]:
            val = recherche.get(cle, "")
            if val and str(val).strip():
                rech_propre[cle] = str(val).strip()
        domaines = [str(x).strip() for x in recherche.get("domaines", []) if x and str(x).strip()]
        if domaines:
            rech_propre["domaines"] = domaines
        if rech_propre:
            propre["recherche"] = rech_propre

    return propre
