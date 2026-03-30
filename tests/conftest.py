"""
conftest.py — Fixtures partagées par tous les tests
=====================================================

CONCEPT CLÉ : les fixtures pytest.

Une fixture crée un contexte réutilisable pour les tests :
- tmp_path : dossier temporaire (nettoyé automatiquement)
- offre_sample : une offre de test prête à l'emploi
- candidature_sample : une candidature de test

pytest les injecte automatiquement dans les fonctions de test
qui les demandent en paramètre.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def offre_data():
    """Données brutes d'une offre (dict)."""
    return {
        "titre": "Alternance Développeur Python",
        "entreprise": "TechCorp",
        "url": "https://wttj.com/jobs/dev-python",
        "source": "wttj",
        "lieu": "Paris",
        "description": "Développement backend Python, API REST, Docker.",
        "type_contrat": "Alternance",
        "salaire": "1200 EUR / mois",
        "date_publication": "2026-03-15",
        "score": 75,
    }


@pytest.fixture
def offre_data_2():
    """Deuxième offre pour les tests de déduplication."""
    return {
        "titre": "Alternance DevOps Cloud",
        "entreprise": "CloudNine",
        "url": "https://wttj.com/jobs/devops",
        "source": "wttj",
        "lieu": "La Défense",
        "description": "CI/CD, Kubernetes, AWS.",
        "type_contrat": "Alternance",
        "score": 60,
    }


@pytest.fixture
def candidature_data():
    """Données brutes d'une candidature (dict)."""
    return {
        "offre_id": "wttj_abc123",
        "titre": "Alternance Développeur Python",
        "entreprise": "TechCorp",
        "lieu": "Paris",
        "score": 75,
        "url": "https://wttj.com/jobs/dev-python",
        "etat": "brouillon",
        "historique": [
            {"etat": "brouillon", "date": "2026-03-20T10:00:00", "commentaire": "Création du suivi"}
        ],
        "notes": [],
        "date_creation": "2026-03-20T10:00:00",
        "date_relance": "",
        "fichiers": {},
    }


@pytest.fixture
def fichier_offres_json(tmp_path, offre_data, offre_data_2):
    """Crée un fichier offres.json temporaire avec 2 offres."""
    # Ajouter les IDs (simuler __post_init__)
    offre_data["id"] = "wttj_aaa111"
    offre_data_2["id"] = "wttj_bbb222"

    data = [offre_data, offre_data_2]
    chemin = tmp_path / "offres.json"
    chemin.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return chemin


@pytest.fixture
def fichier_suivi_json(tmp_path, candidature_data):
    """Crée un fichier suivi.json temporaire avec 1 candidature."""
    data = [candidature_data]
    chemin = tmp_path / "suivi.json"
    chemin.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return chemin


@pytest.fixture
def env_file(tmp_path):
    """Crée un fichier .env temporaire."""
    env = tmp_path / ".env"
    env.write_text(
        'ANTHROPIC_API_KEY=sk-ant-api03-FAKE-TEST-KEY-123\n'
        'ANTHROPIC_MODEL=claude-sonnet-4-20250514\n'
        'SCORE_MINIMUM=70\n'
        '# ceci est un commentaire\n'
        '\n'
        'VALEUR_GUILLEMETS="hello world"\n'
        "VALEUR_SIMPLE=42\n",
        encoding="utf-8",
    )
    return env
