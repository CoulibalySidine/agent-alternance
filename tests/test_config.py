"""
test_config.py — Tests pour config.py
=======================================

Teste :
- Parsing du .env (clé=valeur, commentaires, guillemets)
- Valeurs par défaut
- Conversion de types (int, float)
- Validation de la config
"""

import os
import pytest
from pathlib import Path


class TestChargerEnv:
    """Tests du parsing .env."""

    def test_parsing_basique(self, tmp_path):
        """CLÉ=valeur est correctement parsé."""
        from config import _charger_env
        env = tmp_path / ".env"
        env.write_text("MA_CLE=ma_valeur\n")
        result = _charger_env(env)
        assert result["MA_CLE"] == "ma_valeur"

    def test_commentaires_ignores(self, tmp_path):
        from config import _charger_env
        env = tmp_path / ".env"
        env.write_text("# commentaire\nCLE=val\n")
        result = _charger_env(env)
        assert "#" not in str(result.keys())
        assert result["CLE"] == "val"

    def test_lignes_vides_ignorees(self, tmp_path):
        from config import _charger_env
        env = tmp_path / ".env"
        env.write_text("CLE1=a\n\n\nCLE2=b\n")
        result = _charger_env(env)
        assert len(result) == 2

    def test_guillemets_doubles_retires(self, tmp_path):
        from config import _charger_env
        env = tmp_path / ".env"
        env.write_text('CLE="hello world"\n')
        result = _charger_env(env)
        assert result["CLE"] == "hello world"

    def test_guillemets_simples_retires(self, tmp_path):
        from config import _charger_env
        env = tmp_path / ".env"
        env.write_text("CLE='hello world'\n")
        result = _charger_env(env)
        assert result["CLE"] == "hello world"

    def test_fichier_inexistant(self, tmp_path):
        from config import _charger_env
        result = _charger_env(tmp_path / "nexiste_pas")
        assert result == {}

    def test_valeur_avec_egal(self, tmp_path):
        """Une valeur contenant = est correctement parsée (split au premier =)."""
        from config import _charger_env
        env = tmp_path / ".env"
        env.write_text("CLE=a=b=c\n")
        result = _charger_env(env)
        assert result["CLE"] == "a=b=c"

    def test_ligne_sans_egal_ignoree(self, tmp_path):
        from config import _charger_env
        env = tmp_path / ".env"
        env.write_text("PAS_UNE_CLE\nCLE=val\n")
        result = _charger_env(env)
        assert len(result) == 1
        assert result["CLE"] == "val"


class TestEnvHelpers:
    """Tests des fonctions env(), env_int(), env_float()."""

    def test_env_defaut(self):
        from config import env
        # Clé qui n'existe certainement pas
        result = env("CLE_QUI_NEXISTE_PAS_12345", "fallback")
        assert result == "fallback"

    def test_env_int_conversion(self):
        from config import env_int
        os.environ["TEST_INT_KEY"] = "42"
        assert env_int("TEST_INT_KEY") == 42
        del os.environ["TEST_INT_KEY"]

    def test_env_int_fallback(self):
        from config import env_int
        result = env_int("CLE_INEXISTANTE_INT", 99)
        assert result == 99

    def test_env_int_valeur_invalide(self):
        from config import env_int
        os.environ["TEST_BAD_INT"] = "pas_un_nombre"
        result = env_int("TEST_BAD_INT", 7)
        assert result == 7
        del os.environ["TEST_BAD_INT"]

    def test_env_float_conversion(self):
        from config import env_float
        os.environ["TEST_FLOAT_KEY"] = "3.14"
        assert env_float("TEST_FLOAT_KEY") == pytest.approx(3.14)
        del os.environ["TEST_FLOAT_KEY"]

    def test_env_float_fallback(self):
        from config import env_float
        result = env_float("CLE_INEXISTANTE_FLOAT", 1.5)
        assert result == pytest.approx(1.5)


class TestVerifierConfig:
    """Tests de la validation de config."""

    def test_cle_manquante_detectee(self, monkeypatch):
        """verifier_config() retourne False si la clé API est vide."""
        # On force API_KEY à vide dans le module config
        import config
        monkeypatch.setattr(config, "API_KEY", "")
        assert config.verifier_config() is False

    def test_cle_invalide_detectee(self, monkeypatch):
        """verifier_config() retourne False si la clé ne commence pas par sk-ant-."""
        import config
        monkeypatch.setattr(config, "API_KEY", "cle-invalide-123")
        assert config.verifier_config() is False

    def test_cle_valide_acceptee(self, monkeypatch):
        import config
        monkeypatch.setattr(config, "API_KEY", "sk-ant-api03-FAKE-KEY-FOR-TESTING")
        assert config.verifier_config() is True
