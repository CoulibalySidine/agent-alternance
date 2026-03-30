"""
test_tracker.py — Tests pour suivi/tracker.py
===============================================

Teste :
- Machine à états (changement d'état, historique)
- Sérialisation roundtrip (to_dict / from_dict avec inspect)
- Logique de relance
- Notes
- Fonctions de nettoyage
"""

import json
import pytest
from datetime import datetime, timedelta
from suivi.tracker import (
    Candidature, ETATS, DELAI_RELANCE,
    charger_suivi, sauvegarder_suivi,
)


class TestCandidatureCreation:
    """Tests de création d'une Candidature."""

    def test_creation_basique(self):
        c = Candidature(offre_id="test_123", titre="Dev Python", entreprise="Corp")
        assert c.offre_id == "test_123"
        assert c.titre == "Dev Python"
        assert c.etat == "brouillon"

    def test_valeurs_par_defaut(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        assert c.lieu == ""
        assert c.score is None
        assert c.notes == []
        assert c.fichiers == {}
        assert c.date_relance == ""

    def test_historique_auto_creation(self):
        """L'historique contient automatiquement l'état initial."""
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        assert len(c.historique) == 1
        assert c.historique[0]["etat"] == "brouillon"
        assert c.historique[0]["commentaire"] == "Création du suivi"

    def test_historique_pas_duplique_si_fourni(self):
        """Si on fournit un historique, pas d'ajout auto."""
        hist = [{"etat": "envoyee", "date": "2026-01-01", "commentaire": "test"}]
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp", historique=hist)
        assert len(c.historique) == 1
        assert c.historique[0]["etat"] == "envoyee"

    def test_date_creation_auto(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        assert c.date_creation != ""
        # Doit être parseable
        datetime.fromisoformat(c.date_creation)


class TestMachineAEtats:
    """Tests du changement d'état."""

    def test_changer_etat_valide(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.changer_etat("envoyee")
        assert c.etat == "envoyee"

    def test_historique_mis_a_jour(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.changer_etat("envoyee", "Envoyée par email")
        assert len(c.historique) == 2
        assert c.historique[1]["etat"] == "envoyee"
        assert c.historique[1]["commentaire"] == "Envoyée par email"

    def test_etat_inconnu_rejete(self):
        """Un état invalide ne change rien."""
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.changer_etat("etat_bidon")
        assert c.etat == "brouillon"  # Pas changé
        assert len(c.historique) == 1  # Pas d'entrée ajoutée

    def test_tous_les_etats_valides(self):
        """Tous les états définis dans ETATS sont acceptés."""
        for etat in ETATS:
            c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
            c.changer_etat(etat)
            assert c.etat == etat

    def test_parcours_complet(self):
        """Simule le parcours brouillon → envoyee → vue → entretien → acceptee."""
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        parcours = ["envoyee", "vue", "entretien", "acceptee"]
        for etat in parcours:
            c.changer_etat(etat)
        assert c.etat == "acceptee"
        assert len(c.historique) == 5  # initial + 4 changements

    def test_date_relance_fixee_apres_envoi(self):
        """Changer à 'envoyee' fixe une date de relance à J+7."""
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.changer_etat("envoyee")
        assert c.date_relance != ""
        relance = datetime.fromisoformat(c.date_relance)
        # La relance doit être dans ~7 jours (±1 seconde)
        attendu = datetime.now() + timedelta(days=DELAI_RELANCE["envoyee"])
        assert abs((relance - attendu).total_seconds()) < 2

    def test_date_relance_effacee_si_acceptee(self):
        """Passer à 'acceptee' efface la date de relance."""
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.changer_etat("envoyee")
        assert c.date_relance != ""
        c.changer_etat("acceptee")
        assert c.date_relance == ""


class TestRelance:
    """Tests de la logique de relance."""

    def test_pas_de_relance_si_brouillon(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        assert c.doit_relancer() is False

    def test_pas_de_relance_si_acceptee(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp", etat="acceptee")
        c.date_relance = datetime.now().isoformat()  # Même si date passée
        assert c.doit_relancer() is False

    def test_pas_de_relance_si_refusee(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp", etat="refusee")
        c.date_relance = datetime.now().isoformat()
        assert c.doit_relancer() is False

    def test_relance_si_date_passee(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp", etat="envoyee")
        c.date_relance = (datetime.now() - timedelta(days=1)).isoformat()
        assert c.doit_relancer() is True

    def test_pas_de_relance_si_date_future(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp", etat="envoyee")
        c.date_relance = (datetime.now() + timedelta(days=5)).isoformat()
        assert c.doit_relancer() is False


class TestJoursDepuisEnvoi:
    """Tests du calcul de jours depuis l'envoi."""

    def test_none_si_jamais_envoyee(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        assert c.jours_depuis_envoi() is None

    def test_jours_calcules(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        # Simuler un envoi il y a 3 jours
        c.historique.append({
            "etat": "envoyee",
            "date": (datetime.now() - timedelta(days=3)).isoformat(),
            "commentaire": "test",
        })
        assert c.jours_depuis_envoi() == 3


class TestNotes:
    """Tests de l'ajout de notes."""

    def test_ajouter_note(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.ajouter_note("Premier contact positif")
        assert len(c.notes) == 1
        assert c.notes[0]["texte"] == "Premier contact positif"
        assert "date" in c.notes[0]

    def test_plusieurs_notes(self):
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.ajouter_note("Note 1")
        c.ajouter_note("Note 2")
        assert len(c.notes) == 2


class TestSerialization:
    """Tests de sérialisation Candidature."""

    def test_roundtrip(self, candidature_data):
        """to_dict() → from_dict() redonne le même objet."""
        original = Candidature.from_dict(candidature_data)
        data = original.to_dict()
        restored = Candidature.from_dict(data)

        assert restored.offre_id == original.offre_id
        assert restored.titre == original.titre
        assert restored.etat == original.etat
        assert restored.score == original.score

    def test_from_dict_ignore_cles_inconnues(self):
        """from_dict() n'injecte pas de clés non-paramètres."""
        data = {
            "offre_id": "x", "titre": "Dev", "entreprise": "Corp",
            "champ_bidon": "DANGER", "self": "NOPE",
        }
        c = Candidature.from_dict(data)
        assert c.titre == "Dev"
        assert not hasattr(c, "champ_bidon")

    def test_from_dict_ne_crashe_pas_sur_self(self):
        """Le fix inspect empêche 'self' de passer en paramètre."""
        data = {
            "offre_id": "x", "titre": "Dev", "entreprise": "Corp",
            "self": "this_should_be_ignored",
        }
        # Avant le fix, ça crashait avec TypeError
        c = Candidature.from_dict(data)
        assert c.offre_id == "x"


class TestStockageSuivi:
    """Tests de sauvegarde / chargement du suivi."""

    def test_sauvegarder_et_charger(self, tmp_path):
        candidatures = [
            Candidature(offre_id="a", titre="Dev Python", entreprise="Corp A"),
            Candidature(offre_id="b", titre="Dev Java", entreprise="Corp B"),
        ]
        chemin = tmp_path / "suivi.json"
        sauvegarder_suivi(candidatures, chemin)

        loaded = charger_suivi(chemin)
        assert len(loaded) == 2
        assert loaded[0].titre == "Dev Python"
        assert loaded[1].titre == "Dev Java"

    def test_charger_fichier_inexistant(self, tmp_path):
        chemin = tmp_path / "nexiste_pas.json"
        result = charger_suivi(chemin)
        assert result == []

    def test_etat_preserve_apres_sauvegarde(self, tmp_path):
        """Un changement d'état est bien sauvegardé et rechargé."""
        c = Candidature(offre_id="x", titre="Dev", entreprise="Corp")
        c.changer_etat("envoyee", "Email envoyé")

        chemin = tmp_path / "suivi.json"
        sauvegarder_suivi([c], chemin)

        loaded = charger_suivi(chemin)
        assert loaded[0].etat == "envoyee"
        assert len(loaded[0].historique) == 2

    def test_resume_format(self):
        """Le résumé contient les infos essentielles."""
        c = Candidature(offre_id="x", titre="Dev Python", entreprise="TechCorp", etat="envoyee")
        r = c.résumé()
        assert "Dev Python" in r
        assert "TechCorp" in r
        assert "envoyee" in r
