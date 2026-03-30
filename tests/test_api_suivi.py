"""
test_api_suivi.py — Tests des endpoints Suivi
===============================================

Teste : GET /suivi, GET /suivi/stats, POST /suivi,
        PATCH /suivi/{id}/etat, DELETE /suivi/{id}
"""

import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


OFFRES = [
    {
        "titre": "Dev Python", "entreprise": "TechCorp",
        "url": "https://ex.com/1", "source": "wttj", "lieu": "Paris",
        "description": "Dev", "type_contrat": "Alternance",
        "id": "wttj_001", "date_collecte": "2025-01-15T10:00:00",
        "score": 80.0, "salaire": None, "date_publication": None,
        "raison_score": None, "points_forts": None, "points_faibles": None, "conseil": None,
    },
    {
        "titre": "Data Analyst", "entreprise": "DataCo",
        "url": "https://ex.com/2", "source": "wttj", "lieu": "Lyon",
        "description": "Data", "type_contrat": "Alternance",
        "id": "wttj_002", "date_collecte": "2025-01-16T10:00:00",
        "score": 65.0, "salaire": None, "date_publication": None,
        "raison_score": None, "points_forts": None, "points_faibles": None, "conseil": None,
    },
]

SUIVI = [
    {
        "offre_id": "wttj_002", "titre": "Data Analyst",
        "entreprise": "DataCo", "lieu": "Lyon", "score": 65.0,
        "url": "https://ex.com/2", "etat": "brouillon",
        "historique": [{"etat": "brouillon", "date": "2025-01-20T10:00:00", "commentaire": "Création"}],
        "notes": [], "date_creation": "2025-01-20T10:00:00",
        "date_relance": "", "fichiers": {},
    },
]


@pytest.fixture
def client(tmp_path):
    offres_path = tmp_path / "offres.json"
    suivi_path = tmp_path / "suivi.json"
    offres_path.write_text(json.dumps(OFFRES, ensure_ascii=False), encoding="utf-8")
    suivi_path.write_text(json.dumps(SUIVI, ensure_ascii=False), encoding="utf-8")

    with patch("sourcing.models.FICHIER_OFFRES", offres_path), \
         patch("suivi.tracker.SUIVI_PATH", suivi_path):
        from api.main import app
        yield TestClient(app)


# ============================================================
# GET /suivi
# ============================================================

class TestListerSuivi:

    def test_liste_toutes(self, client):
        r = client.get("/suivi")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["offre_id"] == "wttj_002"

    def test_filtre_etat(self, client):
        r = client.get("/suivi?etat=brouillon")
        data = r.json()
        assert len(data) == 1

    def test_filtre_etat_vide(self, client):
        r = client.get("/suivi?etat=acceptee")
        data = r.json()
        assert len(data) == 0

    def test_filtre_entreprise(self, client):
        r = client.get("/suivi?entreprise=data")
        data = r.json()
        assert len(data) == 1


# ============================================================
# GET /suivi/stats
# ============================================================

class TestStatsSuivi:

    def test_stats(self, client):
        r = client.get("/suivi/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["par_etat"]["brouillon"] == 1
        assert data["score_moyen"] == 65.0


# ============================================================
# POST /suivi — Ajouter au suivi
# ============================================================

class TestAjouterSuivi:

    def test_ajouter(self, client):
        r = client.post("/suivi", json={"offre_id": "wttj_001"})
        assert r.status_code == 200
        data = r.json()
        assert data["offre_id"] == "wttj_001"
        assert data["etat"] == "brouillon"
        assert data["titre"] == "Dev Python"

        # Vérifier que le suivi a maintenant 2 entrées
        r2 = client.get("/suivi")
        assert len(r2.json()) == 2

    def test_ajouter_doublon(self, client):
        r = client.post("/suivi", json={"offre_id": "wttj_002"})
        assert r.status_code == 409  # déjà dans le suivi

    def test_ajouter_offre_inexistante(self, client):
        r = client.post("/suivi", json={"offre_id": "fake_999"})
        assert r.status_code == 404

    def test_ajouter_avec_note(self, client):
        r = client.post("/suivi", json={"offre_id": "wttj_001", "notes": "Offre intéressante"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["notes"]) == 1
        assert data["notes"][0]["texte"] == "Offre intéressante"


# ============================================================
# PATCH /suivi/{id}/etat — Changer l'état
# ============================================================

class TestChangerEtat:

    def test_changer_etat_valide(self, client):
        r = client.patch("/suivi/wttj_002/etat", json={"nouvel_etat": "envoyee"})
        assert r.status_code == 200
        data = r.json()
        assert data["etat"] == "envoyee"
        assert len(data["historique"]) == 2

    def test_changer_etat_avec_commentaire(self, client):
        r = client.patch("/suivi/wttj_002/etat", json={
            "nouvel_etat": "envoyee",
            "commentaire": "Envoyé via WTTJ"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["historique"][-1]["commentaire"] == "Envoyé via WTTJ"

    def test_changer_etat_inconnu(self, client):
        r = client.patch("/suivi/wttj_002/etat", json={"nouvel_etat": "etat_bidon"})
        assert r.status_code == 422  # Pydantic validation error (not in enum)

    def test_changer_etat_offre_inexistante(self, client):
        r = client.patch("/suivi/fake_999/etat", json={"nouvel_etat": "envoyee"})
        assert r.status_code == 404


# ============================================================
# DELETE /suivi/{id}
# ============================================================

class TestRetirerSuivi:

    def test_retirer(self, client):
        r = client.delete("/suivi/wttj_002")
        assert r.status_code == 200

        r2 = client.get("/suivi")
        assert len(r2.json()) == 0

    def test_retirer_inexistant(self, client):
        r = client.delete("/suivi/fake_999")
        assert r.status_code == 404
