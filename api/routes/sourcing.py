"""
routes/sourcing.py — Endpoints du module Sourcing
===================================================

GET  /offres          → Liste des offres (filtres, tri, pagination)
GET  /offres/{id}     → Détail d'une offre
POST /offres/scrape   → Lancer un scraping
DELETE /offres/{id}   → Supprimer une offre
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from sourcing.models import Offre, charger_offres, sauvegarder_offres
from api.schemas import OffreResponse, ScrapeRequest, ScrapeResponse

router = APIRouter(prefix="/offres", tags=["Sourcing"])


# ============================================================
# GET /offres — Liste avec filtres
# ============================================================

@router.get("", response_model=list[OffreResponse])
def lister_offres(
    source: Optional[str] = Query(None, description="Filtrer par source (wttj, indeed, demo)"),
    lieu: Optional[str] = Query(None, description="Filtrer par lieu (recherche partielle)"),
    score_min: Optional[float] = Query(None, ge=0, le=100, description="Score minimum"),
    score_max: Optional[float] = Query(None, ge=0, le=100, description="Score maximum"),
    scorees_only: bool = Query(False, description="Uniquement les offres scorées"),
    non_scorees_only: bool = Query(False, description="Uniquement les offres non scorées"),
    recherche: Optional[str] = Query(None, description="Recherche dans titre/entreprise/description"),
    tri: str = Query("score", description="Champ de tri : score, titre, entreprise, date"),
    ordre: str = Query("desc", description="Ordre : asc ou desc"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
):
    """
    Liste les offres avec filtres, tri et pagination.

    Exemples :
    - /offres?score_min=70&tri=score → Top offres
    - /offres?source=wttj&lieu=Paris → Offres WTTJ à Paris
    - /offres?non_scorees_only=true → Offres à scorer
    - /offres?recherche=python&tri=score → Recherche "python"
    """
    offres = charger_offres()

    # --- Filtres ---
    if source:
        offres = [o for o in offres if o.source == source]

    if lieu:
        lieu_lower = lieu.lower()
        offres = [o for o in offres if lieu_lower in (o.lieu or "").lower()]

    if scorees_only:
        offres = [o for o in offres if o.score is not None]
    elif non_scorees_only:
        offres = [o for o in offres if o.score is None]

    if score_min is not None:
        offres = [o for o in offres if (o.score or 0) >= score_min]
    if score_max is not None:
        offres = [o for o in offres if (o.score or 0) <= score_max]

    if recherche:
        r = recherche.lower()
        offres = [
            o for o in offres
            if r in (o.titre or "").lower()
            or r in (o.entreprise or "").lower()
            or r in (o.description or "").lower()
        ]

    # --- Tri ---
    reverse = (ordre == "desc")
    if tri == "score":
        offres.sort(key=lambda o: o.score or 0, reverse=reverse)
    elif tri == "titre":
        offres.sort(key=lambda o: (o.titre or "").lower(), reverse=reverse)
    elif tri == "entreprise":
        offres.sort(key=lambda o: (o.entreprise or "").lower(), reverse=reverse)
    elif tri == "date":
        offres.sort(key=lambda o: o.date_collecte or "", reverse=reverse)

    # --- Pagination ---
    offres = offres[offset:offset + limit]

    return [_offre_to_response(o) for o in offres]


# ============================================================
# GET /offres/{id} — Détail
# ============================================================

@router.get("/{offre_id}", response_model=OffreResponse)
def detail_offre(offre_id: str):
    """Retourne le détail d'une offre par son ID."""
    offre = _trouver_offre(offre_id)
    return _offre_to_response(offre)


# ============================================================
# DELETE /offres/{id} — Supprimer
# ============================================================

@router.delete("/{offre_id}")
def supprimer_offre(offre_id: str):
    """Supprime une offre de la base."""
    offres = charger_offres()
    avant = len(offres)
    offres = [o for o in offres if o.id != offre_id]
    if len(offres) == avant:
        raise HTTPException(status_code=404, detail=f"Offre {offre_id} introuvable")
    sauvegarder_offres(offres)
    return {"message": f"Offre {offre_id} supprimée", "restantes": len(offres)}


# ============================================================
# POST /offres/scrape — Lancer un scraping
# ============================================================

@router.post("/scrape", response_model=ScrapeResponse)
def lancer_scrape(params: ScrapeRequest):
    """
    Lance le scraping avec les paramètres demandés.

    Le scraping est synchrone car il dure généralement < 30s.
    Les nouvelles offres sont dédupliquées et ajoutées à offres.json.
    """
    from sourcing.runner import lancer_collecte

    offres_avant = len(charger_offres())
    erreurs = []

    try:
        lancer_collecte(
            mot_cle=params.mot_cle,
            ville=params.ville,
            max_pages=params.max_pages,
            mode_demo=params.mode_demo,
        )
    except Exception as e:
        erreurs.append(str(e))

    offres_apres = charger_offres()
    nouvelles = len(offres_apres) - offres_avant

    return ScrapeResponse(
        nouvelles_offres=max(0, nouvelles),
        total_offres=len(offres_apres),
        erreurs=erreurs,
    )


# ============================================================
# Helpers
# ============================================================

def _trouver_offre(offre_id: str) -> Offre:
    """Cherche une offre par ID ou lève 404."""
    offres = charger_offres()
    for o in offres:
        if o.id == offre_id:
            return o
    raise HTTPException(status_code=404, detail=f"Offre {offre_id} introuvable")


def _offre_to_response(offre: Offre) -> OffreResponse:
    """Convertit un objet Offre en réponse API."""
    return OffreResponse(
        id=offre.id,
        titre=offre.titre,
        entreprise=offre.entreprise,
        lieu=offre.lieu,
        type_contrat=offre.type_contrat,
        salaire=offre.salaire,
        description=offre.description,
        url=offre.url,
        source=offre.source,
        date_collecte=offre.date_collecte,
        score=offre.score,
        raison_score=offre.raison_score,
        points_forts=offre.points_forts,
        points_faibles=offre.points_faibles,
        conseil=offre.conseil,
    )
