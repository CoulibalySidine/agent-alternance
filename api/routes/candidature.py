"""
routes/candidature.py — Endpoints du module Candidature
========================================================

POST /candidatures/{id}/generer  → Générer un dossier complet (async)
GET  /candidatures/{id}/fichiers → Lister les fichiers générés
GET  /candidatures/{id}/fichiers/{nom} → Télécharger un fichier
"""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from sourcing.models import charger_offres
from api.schemas import (
    GenererDossierRequest, FichierResponse,
    TaskResponse, TaskStatus,
)
from api.tasks import task_manager, Task
from api.deps import get_api_key
from logger import get_logger

log = get_logger("api.candidature")

router = APIRouter(prefix="/candidatures", tags=["Candidature"])

# Dossier racine des candidatures générées
LETTRES_DIR = Path(__file__).parent.parent.parent / "candidature" / "lettres"


# ============================================================
# POST /candidatures/{id}/generer — Générer un dossier (async)
# ============================================================

@router.post("/{offre_id}/generer", response_model=TaskResponse)
def generer_dossier(
    offre_id: str,
    params: GenererDossierRequest = GenererDossierRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    api_key: str = Depends(get_api_key),
):
    """
    Génère un dossier de candidature complet pour une offre :
    - CV adapté (Word)
    - Lettre de motivation (Word + PDF)
    - Fiche de préparation entretien (Markdown)
    - Réponses formulaire (Markdown)

    Retourne un task_id pour suivre la progression.
    """
    offres = charger_offres()
    offre = next((o for o in offres if o.id == offre_id), None)
    if not offre:
        raise HTTPException(status_code=404, detail=f"Offre {offre_id} introuvable")

    task = task_manager.create("generation_dossier")
    background_tasks.add_task(
        _generer_dossier_complet, task, offre.to_dict(), api_key, params,
    )

    log.info(f"Tâche génération créée : {task.id} pour {offre.titre} @ {offre.entreprise}")
    return TaskResponse(**task.to_dict())


# ============================================================
# GET /candidatures/{id}/fichiers — Lister les fichiers
# ============================================================

@router.get("/{offre_id}/fichiers", response_model=list[FichierResponse])
def lister_fichiers(offre_id: str):
    """Liste les fichiers générés pour une offre."""
    offres = charger_offres()
    offre = next((o for o in offres if o.id == offre_id), None)
    if not offre:
        raise HTTPException(status_code=404, detail=f"Offre {offre_id} introuvable")

    return _trouver_fichiers_offre(offre)


# ============================================================
# GET /candidatures/{id}/fichiers/{nom} — Télécharger
# ============================================================

@router.get("/{offre_id}/fichiers/{nom_fichier}")
def telecharger_fichier(offre_id: str, nom_fichier: str):
    """Télécharge un fichier généré pour une offre."""
    offres = charger_offres()
    offre = next((o for o in offres if o.id == offre_id), None)
    if not offre:
        raise HTTPException(status_code=404, detail=f"Offre {offre_id} introuvable")

    if not LETTRES_DIR.exists():
        raise HTTPException(status_code=404, detail="Aucun dossier de candidature trouvé")

    for dossier in LETTRES_DIR.iterdir():
        if dossier.is_dir():
            fichier = dossier / nom_fichier
            if fichier.exists():
                return FileResponse(
                    path=str(fichier),
                    filename=nom_fichier,
                    media_type="application/octet-stream",
                )

    raise HTTPException(status_code=404, detail=f"Fichier {nom_fichier} introuvable")


# ============================================================
# Génération en arrière-plan
# ============================================================

def _generer_dossier_complet(
    task: Task,
    offre_dict: dict,
    api_key: str,
    params: GenererDossierRequest,
):
    """Génère tous les documents de candidature (exécuté en BackgroundTask)."""
    try:
        task_manager.update(task.id, status=TaskStatus.RUNNING, progress="Préparation...")

        entreprise = offre_dict.get("entreprise", "entreprise")
        titre = offre_dict.get("titre", "poste")

        # Créer le dossier de sortie (même logique que candidature/runner.py)
        nom_dossier = f"{entreprise}".replace(" ", "_").replace("/", "-")
        nom_dossier = "".join(c for c in nom_dossier if c.isalnum() or c in "_-")[:40]
        output_dir = LETTRES_DIR / nom_dossier
        output_dir.mkdir(parents=True, exist_ok=True)

        fichiers_generes = []
        etapes_total = sum([params.generer_cv, params.generer_lettre,
                           params.generer_fiche, params.generer_reponses])
        etape_courante = 0

        # --- 1. CV adapté ---
        if params.generer_cv:
            etape_courante += 1
            task_manager.update(
                task.id,
                progress=f"[{etape_courante}/{etapes_total}] Génération du CV adapté...",
            )
            try:
                from candidature.cv_adapter import CVAdapter
                adapter = CVAdapter(api_key=api_key)
                chemin = adapter.generer_cv(offre_dict, output_dir)
                if chemin:
                    fichiers_generes.append(FichierResponse(
                        nom=chemin.name, type="cv", chemin=str(chemin),
                    ))
            except Exception as e:
                log.warning(f"Erreur génération CV : {e}")

        # --- 2. Lettre de motivation ---
        if params.generer_lettre:
            etape_courante += 1
            task_manager.update(
                task.id,
                progress=f"[{etape_courante}/{etapes_total}] Génération de la lettre de motivation...",
            )
            try:
                from candidature.generateur import Generateur
                gen = Generateur(api_key=api_key)
                # generer_pour_offre() retourne un dict avec docx/pdf/txt paths
                # et écrit dans candidature/lettres/ directement
                res = gen.generer_pour_offre(offre_dict)
                if res:
                    # Déplacer les fichiers dans le dossier de l'offre
                    for ext, type_label in [("docx", "lettre_docx"), ("pdf", "lettre_pdf")]:
                        ancien = res.get(ext)
                        if ancien and Path(ancien).exists():
                            nouveau = output_dir / Path(ancien).name
                            Path(ancien).rename(nouveau)
                            fichiers_generes.append(FichierResponse(
                                nom=nouveau.name, type=type_label, chemin=str(nouveau),
                            ))
            except Exception as e:
                log.warning(f"Erreur génération lettre : {e}")

        # --- 3. Fiche entretien ---
        if params.generer_fiche:
            etape_courante += 1
            task_manager.update(
                task.id,
                progress=f"[{etape_courante}/{etapes_total}] Génération de la fiche entretien...",
            )
            try:
                from candidature.fiche_entretien import FicheEntretien
                gen = FicheEntretien(api_key=api_key)
                chemin = gen.sauvegarder_fiche(offre_dict, output_dir)
                if chemin:
                    fichiers_generes.append(FichierResponse(
                        nom=chemin.name, type="fiche", chemin=str(chemin),
                    ))
            except Exception as e:
                log.warning(f"Erreur génération fiche : {e}")

        # --- 4. Réponses formulaire ---
        if params.generer_reponses:
            etape_courante += 1
            task_manager.update(
                task.id,
                progress=f"[{etape_courante}/{etapes_total}] Génération des réponses formulaire...",
            )
            try:
                from candidature.reponses_questions import ReponsesQuestions
                gen = ReponsesQuestions(api_key=api_key)
                chemin = gen.sauvegarder_reponses(
                    offre_dict, output_dir,
                    questions_custom=params.questions_custom,
                )
                if chemin:
                    fichiers_generes.append(FichierResponse(
                        nom=chemin.name, type="reponses", chemin=str(chemin),
                    ))
            except Exception as e:
                log.warning(f"Erreur génération réponses : {e}")

        # Résultat final
        task_manager.complete(task.id, {
            "offre_id": offre_dict.get("id", ""),
            "entreprise": entreprise,
            "fichiers": [f.model_dump() for f in fichiers_generes],
            "nombre_fichiers": len(fichiers_generes),
        })

        log.info(f"Dossier généré : {len(fichiers_generes)} fichiers pour {entreprise}")

    except Exception as e:
        log.error(f"Erreur génération dossier : {e}")
        task_manager.fail(task.id, str(e))


def _trouver_fichiers_offre(offre) -> list[FichierResponse]:
    """Cherche les fichiers déjà générés pour une offre."""
    if not LETTRES_DIR.exists():
        return []

    entreprise = (offre.entreprise or "").replace(" ", "_").replace("/", "-")
    fichiers = []

    for dossier in LETTRES_DIR.iterdir():
        if not dossier.is_dir():
            continue
        if entreprise.lower() not in dossier.name.lower():
            continue

        for f in dossier.iterdir():
            if not f.is_file():
                continue
            nom_lower = f.name.lower()
            if nom_lower.startswith("cv"):
                type_fichier = "cv"
            elif "lm_" in nom_lower and nom_lower.endswith(".docx"):
                type_fichier = "lettre_docx"
            elif "lm_" in nom_lower and nom_lower.endswith(".pdf"):
                type_fichier = "lettre_pdf"
            elif "entretien" in nom_lower:
                type_fichier = "fiche"
            elif "reponses" in nom_lower:
                type_fichier = "reponses"
            else:
                type_fichier = "autre"

            fichiers.append(FichierResponse(
                nom=f.name, type=type_fichier, chemin=str(f),
            ))

    return fichiers
