"""
routes/qualification.py — Endpoints du module Qualification
=============================================================

IMPORTANT : /score/batch est défini AVANT /score/{offre_id}
sinon FastAPI interprète "batch" comme un offre_id.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from sourcing.models import Offre, charger_offres, sauvegarder_offres
from qualification.scorer import Scorer
from api.schemas import (
    ScoreRequest, ScoreBatchRequest,
    TaskResponse, TaskStatus, OffreResponse,
)
from api.tasks import task_manager, Task
from api.deps import get_api_key
from logger import get_logger

log = get_logger("api.qualification")

router = APIRouter(tags=["Qualification"])


# ============================================================
# POST /score/batch — DOIT ÊTRE AVANT /score/{offre_id}
# ============================================================

@router.post("/score/batch", response_model=TaskResponse)
def scorer_batch(
    params: ScoreBatchRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    api_key: str = Depends(get_api_key),
):
    """
    Lance le scoring d'un lot d'offres en arrière-plan.

    - Si `ids` est fourni : score uniquement ces offres
    - Sinon : score les offres non encore évaluées
    - `max_offres` limite le nombre (défaut: 5)
    """
    task = task_manager.create("scoring_batch")
    background_tasks.add_task(
        _scorer_batch_offres, task, params.ids, params.max_offres,
        params.forcer_rescore, api_key,
    )

    log.info(f"Tâche scoring batch créée : {task.id} ({params.max_offres} offres max)")
    return TaskResponse(**task.to_dict())


# ============================================================
# POST /score/{offre_id} — Scorer UNE offre (async)
# ============================================================

@router.post("/score/{offre_id}", response_model=TaskResponse)
def scorer_offre(
    offre_id: str,
    params: ScoreRequest = ScoreRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    api_key: str = Depends(get_api_key),
):
    """
    Lance le scoring d'une offre en arrière-plan.
    Retourne un task_id pour suivre la progression via GET /tasks/{task_id}.
    """
    offres = charger_offres()
    offre = next((o for o in offres if o.id == offre_id), None)
    if not offre:
        raise HTTPException(status_code=404, detail=f"Offre {offre_id} introuvable")

    if offre.score is not None and not params.forcer_rescore:
        return TaskResponse(
            task_id="already_scored",
            status=TaskStatus.DONE,
            result={
                "offres_scorees": 1,
                "scores": [{
                    "id": offre.id,
                    "titre": offre.titre,
                    "entreprise": offre.entreprise,
                    "score": offre.score,
                    "raison": offre.raison_score,
                }],
            }
        )

    task = task_manager.create("scoring_single")
    background_tasks.add_task(_scorer_une_offre, task, offre_id, api_key)

    log.info(f"Tâche scoring créée : {task.id} pour offre {offre_id}")
    return TaskResponse(**task.to_dict())


# ============================================================
# GET /tasks/{task_id} — Consulter l'état d'une tâche
# ============================================================

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def consulter_tache(task_id: str):
    """
    Retourne l'état actuel d'une tâche asynchrone.
    Le frontend poll cet endpoint toutes les 2-3 secondes.
    """
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} introuvable")
    return TaskResponse(**task.to_dict())


# ============================================================
# Fonctions de scoring en arrière-plan
# ============================================================

def _scorer_une_offre(task: Task, offre_id: str, api_key: str):
    """Scoring d'une seule offre (exécuté en BackgroundTask)."""
    try:
        task_manager.update(task.id, status=TaskStatus.RUNNING, progress="Scoring en cours...")

        offres = charger_offres()
        offre = next((o for o in offres if o.id == offre_id), None)
        if not offre:
            task_manager.fail(task.id, f"Offre {offre_id} introuvable")
            return

        scorer = Scorer(api_key=api_key)
        offre_dict = offre.to_dict()
        resultat = scorer.scorer_offre(offre_dict)

        if resultat:
            offre.score = resultat["score"]
            offre.raison_score = resultat.get("raison", "")
            offre.points_forts = resultat.get("points_forts", [])
            offre.points_faibles = resultat.get("points_faibles", [])
            offre.conseil = resultat.get("conseil", "")
            sauvegarder_offres(offres)

            task_manager.complete(task.id, {
                "offres_scorees": 1,
                "scores": [{
                    "id": offre.id,
                    "titre": offre.titre,
                    "entreprise": offre.entreprise,
                    "score": offre.score,
                    "raison": offre.raison_score,
                    "points_forts": offre.points_forts,
                    "points_faibles": offre.points_faibles,
                    "conseil": offre.conseil,
                }],
            })
            log.info(f"Scoring terminé pour {offre.titre}: {offre.score}/100")
        else:
            task_manager.fail(task.id, "Le scoring n'a pas retourné de résultat")

    except Exception as e:
        log.error(f"Erreur scoring offre {offre_id}: {e}")
        task_manager.fail(task.id, str(e))


def _scorer_batch_offres(
    task: Task,
    ids: list[str],
    max_offres: int,
    forcer_rescore: bool,
    api_key: str,
):
    """Scoring d'un lot d'offres (exécuté en BackgroundTask)."""
    try:
        task_manager.update(task.id, status=TaskStatus.RUNNING, progress="Chargement des offres...")

        offres = charger_offres()

        if ids:
            a_scorer = [o for o in offres if o.id in ids]
        elif forcer_rescore:
            a_scorer = offres
        else:
            a_scorer = [o for o in offres if o.score is None]

        a_scorer = a_scorer[:max_offres]

        if not a_scorer:
            task_manager.complete(task.id, {
                "offres_scorees": 0,
                "message": "Aucune offre à scorer",
                "scores": [],
            })
            return

        task_manager.update(task.id, progress=f"0/{len(a_scorer)} offres scorées")

        scorer = Scorer(api_key=api_key)
        index_offres = {o.id: o for o in offres}
        scores_resultats = []

        for i, offre in enumerate(a_scorer):
            task_manager.update(
                task.id,
                progress=f"{i}/{len(a_scorer)} offres scorées — {offre.titre}",
            )

            offre_dict = offre.to_dict()
            resultat = scorer.scorer_offre(offre_dict)

            if resultat and offre.id in index_offres:
                obj = index_offres[offre.id]
                obj.score = resultat["score"]
                obj.raison_score = resultat.get("raison", "")
                obj.points_forts = resultat.get("points_forts", [])
                obj.points_faibles = resultat.get("points_faibles", [])
                obj.conseil = resultat.get("conseil", "")

                scores_resultats.append({
                    "id": obj.id,
                    "titre": obj.titre,
                    "entreprise": obj.entreprise,
                    "score": obj.score,
                    "raison": obj.raison_score,
                })

        sauvegarder_offres(offres)

        scores_list = [s["score"] for s in scores_resultats]
        task_manager.complete(task.id, {
            "offres_scorees": len(scores_resultats),
            "score_moyen": round(sum(scores_list) / len(scores_list)) if scores_list else 0,
            "meilleur_score": max(scores_list) if scores_list else 0,
            "scores": sorted(scores_resultats, key=lambda s: s["score"], reverse=True),
        })

        log.info(f"Scoring batch terminé : {len(scores_resultats)}/{len(a_scorer)} offres")

    except Exception as e:
        log.error(f"Erreur scoring batch : {e}")
        task_manager.fail(task.id, str(e))
