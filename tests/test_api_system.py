"""
test_api_system.py — Tests des endpoints Système et Profil
============================================================

Teste : GET /, GET /health, GET /profil, PUT /profil
"""

import json
import pytest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    offres_path = tmp_path / "offres.json"
    suivi_path = tmp_path / "suivi.json"
    profil_path = tmp_path / "profil.yaml"

    offres_path.write_text("[]", encoding="utf-8")
    suivi_path.write_text("[]", encoding="utf-8")
    profil_path.write_text('nom: "Test"\nemail: "test@test.com"', encoding="utf-8")

    with patch("sourcing.models.FICHIER_OFFRES", offres_path), \
         patch("suivi.tracker.SUIVI_PATH", suivi_path), \
         patch("profil.generateur_profil.PROFIL_PATH", profil_path):
        from api.main import app
        yield TestClient(app)


# ============================================================
# GET / — Page d'accueil
# ============================================================

class TestRacine:

    def test_racine(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["nom"] == "Agent Alternance API"
        assert "profil" in data["endpoints"]
        assert "sourcing" in data["endpoints"]


# ============================================================
# GET /health — Health check
# ============================================================

class TestHealth:

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert "checks" in data
        assert data["checks"]["api"] == "ok"


# ============================================================
# GET /profil — Voir le profil
# ============================================================

class TestVoirProfil:

    def test_profil_existe(self, client):
        r = client.get("/profil")
        assert r.status_code == 200
        data = r.json()
        assert data["existe"] is True
        assert "Test" in data["contenu"]

    def test_profil_inexistant(self, tmp_path):
        offres_path = tmp_path / "offres.json"
        suivi_path = tmp_path / "suivi.json"
        profil_path = tmp_path / "profil_inexistant.yaml"  # n'existe pas

        offres_path.write_text("[]", encoding="utf-8")
        suivi_path.write_text("[]", encoding="utf-8")

        with patch("sourcing.models.FICHIER_OFFRES", offres_path), \
             patch("suivi.tracker.SUIVI_PATH", suivi_path), \
             patch("profil.generateur_profil.PROFIL_PATH", profil_path):
            from api.main import app
            c = TestClient(app)
            r = c.get("/profil")
            assert r.status_code == 200
            data = r.json()
            assert data["existe"] is False
            assert data["contenu"] is None


# ============================================================
# PUT /profil — Modifier le profil
# ============================================================

class TestModifierProfil:

    def test_modifier(self, client):
        nouveau = 'nom: "Nouveau"\nemail: "new@test.com"'
        r = client.put("/profil", json={"contenu": nouveau})
        assert r.status_code == 200

        # Vérifier que le profil a changé
        r2 = client.get("/profil")
        assert "Nouveau" in r2.json()["contenu"]

    def test_modifier_vide(self, client):
        r = client.put("/profil", json={"contenu": ""})
        assert r.status_code == 400

    def test_modifier_espaces(self, client):
        r = client.put("/profil", json={"contenu": "   "})
        assert r.status_code == 400
