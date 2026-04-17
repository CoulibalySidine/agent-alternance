"""
schemas.py — Modèles Pydantic pour l'API
=========================================

Les états et structures sont alignés avec tracker.py et models.py.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ============================================================
# SOURCING
# ============================================================

class OffreResponse(BaseModel):
    """Une offre telle que retournée par l'API."""
    id: str
    titre: str
    entreprise: str
    lieu: str = ""
    type_contrat: str = ""
    salaire: Optional[str] = None
    description: str = ""
    url: str = ""
    source: str = ""
    date_collecte: str = ""
    score: Optional[float] = None
    raison_score: Optional[str] = None
    points_forts: Optional[list[str]] = None
    points_faibles: Optional[list[str]] = None
    conseil: Optional[str] = None
    age_jours: Optional[int] = None 


class ScrapeRequest(BaseModel):
    """Paramètres pour lancer un scraping."""
    mot_cle: str = Field(
        default="alternance développeur",
        description="Mots-clés de recherche"
    )
    ville: str = Field(
        default="Paris",
        description="Ville de recherche"
    )   
    max_pages: int = Field(
        default=3,
        ge=1, le=10,
        description="Nombre max de pages à scraper"
    )
    mode_demo: bool = Field(
        default=False,
        description="Utiliser le scraper demo (données fictives)"
    )
    sources: list[str] = Field(
        default=["wttj", "lba"], 
        description="Sources : wttj, lba, demo"
    )


class ScrapeResponse(BaseModel):
    """Résultat d'un scraping."""
    nouvelles_offres: int
    total_offres: int
    erreurs: list[str] = []


# ============================================================
# QUALIFICATION (Scoring)
# ============================================================

class ScoreRequest(BaseModel):
    """Paramètres pour scorer une ou plusieurs offres."""
    forcer_rescore: bool = Field(
        default=False,
        description="Re-scorer même si déjà évaluée"
    )


class ScoreBatchRequest(BaseModel):
    """Paramètres pour scorer un lot d'offres."""
    ids: list[str] = Field(
        default=[],
        description="IDs des offres à scorer. Vide = toutes les non-scorées."
    )
    max_offres: int = Field(
        default=5,
        ge=1, le=50,
        description="Nombre max d'offres à scorer"
    )
    forcer_rescore: bool = False


class TaskStatus(str, Enum):
    """États possibles d'une tâche asynchrone."""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class TaskResponse(BaseModel):
    """État d'une tâche asynchrone (scoring, génération, etc.)."""
    task_id: str
    status: TaskStatus
    progress: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


# ============================================================
# CANDIDATURE
# ============================================================

class GenererDossierRequest(BaseModel):
    """Options pour la génération d'un dossier de candidature."""
    generer_cv: bool = True
    generer_lettre: bool = True
    generer_fiche: bool = True
    generer_reponses: bool = True
    questions_custom: list[str] = Field(
        default=[],
        description="Questions custom copiées depuis un formulaire"
    )


class FichierResponse(BaseModel):
    """Un fichier généré."""
    nom: str
    type: str  # "cv", "lettre_docx", "lettre_pdf", "fiche", "reponses"
    chemin: str


class DossierResponse(BaseModel):
    """Résultat de la génération d'un dossier."""
    offre_id: str
    entreprise: str
    fichiers: list[FichierResponse]


# ============================================================
# SUIVI — États alignés avec tracker.py
# ============================================================

class EtatCandidature(str, Enum):
    """
    États de la machine à états du suivi.
    Source de vérité : suivi/tracker.py → ETATS dict.
    """
    BROUILLON = "brouillon"
    ENVOYEE = "envoyee"
    VUE = "vue"
    ENTRETIEN = "entretien"
    ACCEPTEE = "acceptee"
    REFUSEE = "refusee"
    SANS_REPONSE = "sans_reponse"


class SuiviEntry(BaseModel):
    """Une entrée dans le suivi des candidatures."""
    offre_id: str
    titre: str
    entreprise: str
    lieu: str = ""
    score: Optional[float] = None
    url: str = ""
    etat: str = "brouillon"
    historique: list[dict] = []
    notes: list[dict] = []
    date_creation: str = ""
    date_relance: str = ""
    fichiers: dict = {}
    doit_relancer: bool = False
    jours_depuis_envoi: Optional[int] = None


class UpdateEtatRequest(BaseModel):
    """Requête pour changer l'état d'une candidature."""
    nouvel_etat: EtatCandidature
    commentaire: Optional[str] = None


class SuiviStatsResponse(BaseModel):
    """Statistiques du suivi."""
    total: int
    par_etat: dict[str, int]
    score_moyen: Optional[float] = None


class AjouterSuiviRequest(BaseModel):
    """Requête pour ajouter une offre au suivi."""
    offre_id: str
    notes: Optional[str] = None
