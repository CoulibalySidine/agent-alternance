"""
test_api_sourcing.py — Tests des endpoints Sourcing
=====================================================

Teste : GET /offres (filtres, tri, pagination), GET /offres/{id}, DELETE /offres/{id}
N'appelle PAS l'API Claude (pas de scoring ni scraping réel).
"""

import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


# --- Fixtures locales ---

OFFRES = [
    {
        "titre": "Développeur Python", "entreprise": "TechCorp",
        "url": "https://ex.com/1", "source": "wttj", "lieu": "Paris",
        "description": "Dev Python alternance", "type_contrat": "Alternance",
        "id": "wttj_001", "date_collecte": "2025-01-15T10:00:00",
        "score": None, "salaire": None, "date_publication": None,
        "raison_score": None, "points_forts": None, "points_faibles": None, "conseil": None,
    },
    {
        "titre": "Data Analyst", "entreprise": "DataCo",
        "url": "https://ex.com/2", "source": "wttj", "lieu": "Lyon",
        "description": "Data en alternance", "type_contrat": "Alternance",
        "id": "wttj_002", "date_collecte": "2025-01-16T10:00:00",
        "score": 75.0, "salaire": None, "date_publication": None,
        "raison_score": "Bon match", "points_forts": ["Python"], "points_faibles": ["Pas de R"], "conseil": "Focus data",
    },
    {
        "titre": "DevOps Junior", "entreprise": "CloudInc",
        "url": "https://ex.com/3", "source": "demo", "lieu": "Paris",
        "description": "DevOps alternance", "type_contrat": "Alternance",
        "id": "demo_003", "date_collecte": "2025-01-17T10:00:00",
        "score": 42.0, "salaire": None, "date_publication": None,
        "raison_score": "Match moyen", "points_forts": ["Linux"], "points_faibles": ["Docker"], "conseil": "Apprendre Docker",
    },
]


@pytest.fixture
def client(tmp_path):
    offres_path = tmp_path / "offres.json"
    offres_path.write_text(json.dumps(OFFRES, ensure_ascii=False), encoding="utf-8")

    with patch("sourcing.models.FICHIER_OFFRES", offres_path):
        from api.main import app
        yield TestClient(app)


# ============================================================
# GET /offres
# ============================================================

class TestListerOffres:

    def test_liste_toutes(self, client):
        r = client.get("/offres")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 3

    def test_filtre_source(self, client):
        r = client.get("/offres?source=demo")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["source"] == "demo"

    def test_filtre_lieu(self, client):
        r = client.get("/offres?lieu=Lyon")
        data = r.json()
        assert len(data) == 1
        assert data[0]["lieu"] == "Lyon"

    def test_filtre_lieu_partiel(self, client):
        r = client.get("/offres?lieu=par")
        data = r.json()
        assert len(data) == 2  # Paris x2

    def test_filtre_scorees_only(self, client):
        r = client.get("/offres?scorees_only=true")
        data = r.json()
        assert len(data) == 2
        assert all(o["score"] is not None for o in data)

    def test_filtre_non_scorees_only(self, client):
        r = client.get("/offres?non_scorees_only=true")
        data = r.json()
        assert len(data) == 1
        assert data[0]["score"] is None

    def test_filtre_score_min(self, client):
        r = client.get("/offres?score_min=70")
        data = r.json()
        assert len(data) == 1
        assert data[0]["score"] == 75

    def test_filtre_recherche(self, client):
        r = client.get("/offres?recherche=python")
        data = r.json()
        assert len(data) == 1
        assert "Python" in data[0]["titre"]

    def test_tri_score_desc(self, client):
        r = client.get("/offres?tri=score&ordre=desc")
        data = r.json()
        scores = [o["score"] or 0 for o in data]
        assert scores == sorted(scores, reverse=True)

    def test_tri_entreprise_asc(self, client):
        r = client.get("/offres?tri=entreprise&ordre=asc")
        data = r.json()
        noms = [o["entreprise"].lower() for o in data]
        assert noms == sorted(noms)

    def test_pagination_limit(self, client):
        r = client.get("/offres?limit=2")
        data = r.json()
        assert len(data) == 2

    def test_pagination_offset(self, client):
        r = client.get("/offres?limit=1&offset=2&tri=date&ordre=asc")
        data = r.json()
        assert len(data) == 1


# ============================================================
# GET /offres/{id}
# ============================================================

class TestDetailOffre:

    def test_detail_existe(self, client):
        r = client.get("/offres/wttj_002")
        assert r.status_code == 200
        data = r.json()
        assert data["titre"] == "Data Analyst"
        assert data["score"] == 75
        assert data["points_forts"] == ["Python"]

    def test_detail_404(self, client):
        r = client.get("/offres/inexistant_999")
        assert r.status_code == 404


# ============================================================
# DELETE /offres/{id}
# ============================================================

class TestDeleteOffre:

    def test_delete_existe(self, client):
        r = client.delete("/offres/demo_003")
        assert r.status_code == 200
        assert r.json()["restantes"] == 2

        # Vérifier que l'offre n'est plus là
        r2 = client.get("/offres")
        ids = [o["id"] for o in r2.json()]
        assert "demo_003" not in ids

    def test_delete_404(self, client):
        r = client.delete("/offres/inexistant")
        assert r.status_code == 404
