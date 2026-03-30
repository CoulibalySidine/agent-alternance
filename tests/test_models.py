"""
test_models.py — Tests pour sourcing/models.py
================================================

Teste :
- Génération d'ID unique
- Sérialisation roundtrip (to_dict / from_dict)
- Rejet des clés inconnues
- Déduplication
- Sauvegarde / chargement JSON
"""

import json
import pytest
from sourcing.models import Offre, sauvegarder_offres, charger_offres, dédupliquer


class TestOffreCreation:
    """Tests de création d'une Offre."""

    def test_creation_basique(self, offre_data):
        offre = Offre(**{k: v for k, v in offre_data.items() if k != "score"})
        assert offre.titre == "Alternance Développeur Python"
        assert offre.entreprise == "TechCorp"
        assert offre.source == "wttj"

    def test_id_auto_genere(self):
        """L'ID est généré automatiquement si non fourni."""
        offre = Offre(titre="Dev", entreprise="Corp", url="http://x", source="test")
        assert offre.id != ""
        assert offre.id.startswith("test_")

    def test_id_deterministe(self):
        """Le même titre+entreprise+url produit le même ID."""
        offre1 = Offre(titre="Dev", entreprise="Corp", url="http://x", source="test")
        offre2 = Offre(titre="Dev", entreprise="Corp", url="http://x", source="test")
        assert offre1.id == offre2.id

    def test_id_different_si_donnees_differentes(self):
        """Des offres différentes ont des IDs différents."""
        offre1 = Offre(titre="Dev Python", entreprise="A", url="http://a", source="test")
        offre2 = Offre(titre="Dev Java", entreprise="B", url="http://b", source="test")
        assert offre1.id != offre2.id

    def test_id_custom_preserve(self):
        """Un ID fourni manuellement est conservé."""
        offre = Offre(titre="Dev", entreprise="Corp", url="http://x", source="test", id="custom_123")
        assert offre.id == "custom_123"

    def test_valeurs_par_defaut(self):
        offre = Offre(titre="Dev", entreprise="Corp", url="http://x", source="test")
        assert offre.lieu == "Non précisé"
        assert offre.type_contrat == "Alternance"
        assert offre.salaire is None
        assert offre.score is None


class TestOffreSerialization:
    """Tests de sérialisation to_dict / from_dict."""

    def test_roundtrip(self):
        """to_dict() → from_dict() redonne le même objet."""
        original = Offre(
            titre="Dev Python", entreprise="TechCorp",
            url="http://test.com", source="wttj",
            lieu="Paris", score=85,
        )
        data = original.to_dict()
        restored = Offre.from_dict(data)

        assert restored.titre == original.titre
        assert restored.entreprise == original.entreprise
        assert restored.id == original.id
        assert restored.score == original.score

    def test_from_dict_ignore_cles_inconnues(self):
        """from_dict() ignore les clés qui ne sont pas des champs."""
        data = {
            "titre": "Dev", "entreprise": "Corp",
            "url": "http://x", "source": "test",
            "champ_inconnu": "SKIP", "autre": 42,
        }
        offre = Offre.from_dict(data)
        assert offre.titre == "Dev"
        assert not hasattr(offre, "champ_inconnu")

    def test_to_dict_contient_tous_les_champs(self):
        offre = Offre(titre="Dev", entreprise="Corp", url="http://x", source="test")
        d = offre.to_dict()
        assert "titre" in d
        assert "entreprise" in d
        assert "id" in d
        assert "date_collecte" in d
        assert "score" in d


class TestDeduplication:
    """Tests de la fonction dédupliquer()."""

    def test_pas_de_doublons(self):
        """Offres avec des IDs différents passent toutes."""
        offre1 = Offre(titre="A", entreprise="X", url="http://1", source="t", id="id1")
        offre2 = Offre(titre="B", entreprise="Y", url="http://2", source="t", id="id2")
        result = dédupliquer([offre1, offre2], [])
        assert len(result) == 2

    def test_doublons_filtres(self):
        """Offres avec le même ID que les existantes sont filtrées."""
        existante = Offre(titre="A", entreprise="X", url="http://1", source="t", id="id1")
        nouvelle = Offre(titre="A", entreprise="X", url="http://1", source="t", id="id1")
        result = dédupliquer([nouvelle], [existante])
        assert len(result) == 0

    def test_mix_nouveaux_et_doublons(self):
        """Seules les offres vraiment nouvelles passent."""
        existante = Offre(titre="A", entreprise="X", url="http://1", source="t", id="id1")
        nouvelle1 = Offre(titre="A", entreprise="X", url="http://1", source="t", id="id1")  # doublon
        nouvelle2 = Offre(titre="B", entreprise="Y", url="http://2", source="t", id="id2")  # nouvelle
        result = dédupliquer([nouvelle1, nouvelle2], [existante])
        assert len(result) == 1
        assert result[0].id == "id2"


class TestStockageJSON:
    """Tests de sauvegarde / chargement JSON."""

    def test_sauvegarder_et_charger(self, tmp_path):
        """Sauvegarder puis charger redonne les mêmes offres."""
        offres = [
            Offre(titre="Dev Python", entreprise="Corp", url="http://x", source="t"),
            Offre(titre="Dev Java", entreprise="Inc", url="http://y", source="t"),
        ]
        chemin = tmp_path / "test_offres.json"
        sauvegarder_offres(offres, chemin)

        loaded = charger_offres(chemin)
        assert len(loaded) == 2
        assert loaded[0].titre == "Dev Python"
        assert loaded[1].titre == "Dev Java"

    def test_charger_fichier_inexistant(self, tmp_path):
        """Charger un fichier inexistant retourne une liste vide."""
        chemin = tmp_path / "nexiste_pas.json"
        result = charger_offres(chemin)
        assert result == []

    def test_fichier_json_valide(self, tmp_path):
        """Le fichier sauvegardé est du JSON valide."""
        offres = [Offre(titre="Dev", entreprise="Corp", url="http://x", source="t")]
        chemin = tmp_path / "test.json"
        sauvegarder_offres(offres, chemin)

        data = json.loads(chemin.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["titre"] == "Dev"

    def test_accents_preserves(self, tmp_path):
        """Les caractères français sont préservés (ensure_ascii=False)."""
        offres = [Offre(titre="Développeur réseau", entreprise="Café", url="http://x", source="t")]
        chemin = tmp_path / "test.json"
        sauvegarder_offres(offres, chemin)

        contenu = chemin.read_text(encoding="utf-8")
        assert "Développeur" in contenu
        assert "Café" in contenu
