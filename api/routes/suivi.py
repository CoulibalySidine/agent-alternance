"""
routes/suivi.py — Endpoints du module Suivi
=============================================

GET    /suivi              → Liste du suivi (toutes les candidatures)
GET    /suivi/stats         → Statistiques du suivi
POST   /suivi              → Ajouter une offre au suivi
PATCH  /suivi/{id}/etat    → Changer l'état d'une candidature
DELETE /suivi/{id}          → Retirer du suivi
GET    /suivi/dashboard     → Dashboard HTML

Types alignés avec suivi/tracker.py :
- charger_suivi()    → list[Candidature]  (objets, pas dicts)
- sauvegarder_suivi() ← list[Candidature]
- États : brouillon, envoyee, vue, entretien, acceptee, refusee, sans_reponse
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
from typing import Optional
from collections import defaultdict          # ← AJOUTER
from datetime import datetime, timedelta     # ← AJOUTER

from suivi.tracker import (
    Candidature, ETATS,
    charger_suivi, sauvegarder_suivi,
)
from api.schemas import (
    SuiviEntry, UpdateEtatRequest, SuiviStatsResponse, AjouterSuiviRequest,
)
from logger import get_logger

log = get_logger("api.suivi")

router = APIRouter(prefix="/suivi", tags=["Suivi"])


# ============================================================
# GET /suivi — Liste du suivi
# ============================================================

@router.get("", response_model=list[SuiviEntry])
def lister_suivi(
    etat: Optional[str] = None,
    entreprise: Optional[str] = None,
):
    """
    Liste toutes les candidatures suivies.

    Filtres optionnels :
    - etat : brouillon, envoyee, vue, entretien, acceptee, refusee, sans_reponse
    - entreprise : recherche partielle dans le nom
    """
    candidatures = charger_suivi()  # → list[Candidature]

    if etat:
        candidatures = [c for c in candidatures if c.etat == etat]

    if entreprise:
        ent_lower = entreprise.lower()
        candidatures = [c for c in candidatures if ent_lower in c.entreprise.lower()]

    return [_candidature_to_response(c) for c in candidatures]


# ============================================================
# GET /suivi/stats — Statistiques
# ============================================================

@router.get("/stats", response_model=SuiviStatsResponse)
def stats_suivi():
    """Retourne les statistiques agrégées du suivi."""
    candidatures = charger_suivi()

    par_etat: dict[str, int] = {}
    scores = []
    for c in candidatures:
        par_etat[c.etat] = par_etat.get(c.etat, 0) + 1
        if c.score is not None:
            scores.append(c.score)

    return SuiviStatsResponse(
        total=len(candidatures),
        par_etat=par_etat,
        score_moyen=round(sum(scores) / len(scores), 1) if scores else None,
    )
    
    
@router.get("/stats/detailed")
def stats_suivi_detailed():
    """Stats enrichies : funnel, conversion, activité, sources."""
    candidatures = charger_suivi()

    if not candidatures:
        return {"total": 0, "funnel": {}, "taux_conversion": {},
                "par_source": {}, "par_lieu": {}, "top_entreprises": [],
                "activite_semaine": [], "score_moyen": None,
                "duree_moyenne_jours": None, "relances": 0}

    par_etat = defaultdict(int)
    par_source = defaultdict(int)
    par_lieu = defaultdict(int)
    par_entreprise = defaultdict(int)
    scores = []

    for c in candidatures:
        par_etat[c.etat] += 1
        source = c.offre_id.split("_")[0] if "_" in c.offre_id else "inconnu"
        par_source[source] += 1
        if c.lieu:
            par_lieu[c.lieu] += 1
        par_entreprise[c.entreprise] += 1
        if c.score is not None:
            scores.append(c.score)

    total = len(candidatures)

    # Funnel
    pipeline = ["brouillon", "envoyee", "vue", "entretien", "acceptee"]
    funnel = {e: sum(1 for c in candidatures
              if any(h.get("etat") == e for h in c.historique) or c.etat == e)
              for e in pipeline}
    funnel["brouillon"] = total

    # Taux de conversion
    taux = {}
    if total > 0:
        taux["global_entretien"] = round(par_etat.get("entretien", 0) / total * 100, 1)
        taux["global_acceptee"] = round(par_etat.get("acceptee", 0) / total * 100, 1)

    # Activité par semaine
    now = datetime.now()
    activite = []
    for i in range(4):
        debut = now - timedelta(weeks=i + 1)
        fin = now - timedelta(weeks=i)
        count = 0
        for c in candidatures:
            try:
                d = datetime.fromisoformat(c.date_creation)
                if debut <= d < fin:
                    count += 1
            except (ValueError, TypeError):
                pass
        activite.append({"semaine": f"S-{i}" if i > 0 else "Cette semaine", "candidatures": count})
    activite.reverse()

    # Durée moyenne
    durees = []
    for c in candidatures:
        try:
            d = datetime.fromisoformat(c.date_creation)
            durees.append((now - d).days)
        except (ValueError, TypeError):
            pass

    top_ent = sorted(par_entreprise.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total": total,
        "par_etat": dict(par_etat),
        "score_moyen": round(sum(scores) / len(scores), 1) if scores else None,
        "funnel": funnel,
        "taux_conversion": taux,
        "par_source": dict(par_source),
        "par_lieu": dict(par_lieu),
        "top_entreprises": [{"entreprise": e, "count": c} for e, c in top_ent],
        "activite_semaine": activite,
        "duree_moyenne_jours": round(sum(durees) / len(durees), 1) if durees else None,
        "relances": sum(1 for c in candidatures if c.doit_relancer()),
    }


# ============================================================
# POST /suivi — Ajouter au suivi
# ============================================================

@router.post("", response_model=SuiviEntry)
def ajouter_au_suivi(params: AjouterSuiviRequest):
    """
    Ajoute une offre au suivi des candidatures.
    L'offre passe à l'état "brouillon" par défaut.
    """
    from sourcing.models import charger_offres

    offres = charger_offres()
    offre = next((o for o in offres if o.id == params.offre_id), None)
    if not offre:
        raise HTTPException(status_code=404, detail=f"Offre {params.offre_id} introuvable")

    # Vérifier si déjà dans le suivi
    candidatures = charger_suivi()
    if any(c.offre_id == params.offre_id for c in candidatures):
        raise HTTPException(status_code=409, detail="Cette offre est déjà dans le suivi")

    # Créer la candidature (objet Candidature, pas un dict)
    nouvelle = Candidature(
        offre_id=offre.id,
        titre=offre.titre,
        entreprise=offre.entreprise,
        lieu=offre.lieu,
        score=offre.score,
        url=offre.url,
    )

    # Ajouter une note initiale si fournie
    if params.notes:
        nouvelle.ajouter_note(params.notes)

    candidatures.append(nouvelle)
    sauvegarder_suivi(candidatures)

    log.info(f"Offre ajoutée au suivi : {offre.titre} @ {offre.entreprise}")
    return _candidature_to_response(nouvelle)


# ============================================================
# PATCH /suivi/{id}/etat — Changer l'état
# ============================================================

@router.patch("/{offre_id}/etat", response_model=SuiviEntry)
def changer_etat(offre_id: str, params: UpdateEtatRequest):
    """
    Change l'état d'une candidature dans le suivi.

    Délègue à Candidature.changer_etat() qui gère :
    - La validation des états (via le dict ETATS de tracker.py)
    - L'historique automatique
    - Les dates de relance automatiques

    États valides : brouillon, envoyee, vue, entretien, acceptee, refusee, sans_reponse
    """
    candidatures = charger_suivi()
    candidature = next((c for c in candidatures if c.offre_id == offre_id), None)
    if not candidature:
        raise HTTPException(
            status_code=404,
            detail=f"Candidature {offre_id} introuvable dans le suivi"
        )

    nouvel_etat = params.nouvel_etat.value

    # Valider que l'état existe dans le tracker
    if nouvel_etat not in ETATS:
        raise HTTPException(
            status_code=400,
            detail=f"État inconnu : {nouvel_etat}. États valides : {', '.join(ETATS.keys())}"
        )

    ancien_etat = candidature.etat

    # Déléguer au modèle (gère historique + dates de relance)
    candidature.changer_etat(
        nouvel_etat,
        commentaire=params.commentaire or "",
    )

    sauvegarder_suivi(candidatures)

    log.info(f"Suivi {offre_id} : {ancien_etat} → {nouvel_etat}")
    return _candidature_to_response(candidature)


# ============================================================
# DELETE /suivi/{id} — Retirer du suivi
# ============================================================

@router.delete("/{offre_id}")
def retirer_du_suivi(offre_id: str):
    """Retire une candidature du suivi."""
    candidatures = charger_suivi()
    avant = len(candidatures)
    candidatures = [c for c in candidatures if c.offre_id != offre_id]

    if len(candidatures) == avant:
        raise HTTPException(status_code=404, detail=f"Candidature {offre_id} introuvable")

    sauvegarder_suivi(candidatures)
    log.info(f"Candidature retirée du suivi : {offre_id}")
    return {"message": f"Candidature {offre_id} retirée du suivi"}


# ============================================================
# GET /suivi/dashboard — Dashboard HTML
# ============================================================

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_html():
    """
    Retourne le dashboard HTML interactif.

    Appelle generer_dashboard() qui génère le fichier HTML,
    puis on lit et retourne le contenu.
    """
    try:
        from suivi.dashboard import generer_dashboard, DASHBOARD_PATH

        # Générer le dashboard (écrit dans dashboard.html)
        generer_dashboard()

        # Lire et retourner le HTML
        if DASHBOARD_PATH.exists():
            html = DASHBOARD_PATH.read_text(encoding="utf-8")
            return HTMLResponse(content=html)
        else:
            raise HTTPException(status_code=500, detail="Dashboard non généré")

    except Exception as e:
        log.error(f"Erreur génération dashboard : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur dashboard : {e}")


# ============================================================
# Helpers
# ============================================================

def _candidature_to_response(c: Candidature) -> SuiviEntry:
    """Convertit un objet Candidature en réponse API."""
    return SuiviEntry(
        offre_id=c.offre_id,
        titre=c.titre,
        entreprise=c.entreprise,
        lieu=c.lieu,
        score=c.score,
        url=c.url,
        etat=c.etat,
        historique=c.historique,
        notes=c.notes,
        date_creation=c.date_creation,
        date_relance=c.date_relance,
        fichiers=c.fichiers,
        doit_relancer=c.doit_relancer(),
        jours_depuis_envoi=c.jours_depuis_envoi(),
    )
