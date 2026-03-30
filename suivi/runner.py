"""
runner.py — Orchestrateur du module Suivi (v3)
===============================================

V3 — print() pour les menus CLI, logger pour les opérations.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from suivi.tracker import (
    Candidature, ETATS, charger_suivi, sauvegarder_suivi,
    importer_offres_qualifiees, nettoyer_offres, dedupliquer_offres,
    purger_offres_demo, reinitialiser_suivi, archiver_offres_sous_seuil
)
from suivi.dashboard import generer_dashboard
from logger import get_logger

log = get_logger("suivi")


def afficher_menu():
    """Menu CLI — reste en print() (c'est de l'UI)."""
    print(f"\n{'='*50}")
    print(f"📋 SUIVI DES CANDIDATURES")
    print(f"{'='*50}")
    print(f"  1. 📥 Importer les offres qualifiées")
    print(f"  2. 📊 Générer le dashboard HTML")
    print(f"  3. 📋 Voir toutes les candidatures")
    print(f"  4. 🔔 Voir les relances à faire")
    print(f"  5. ✏️  Changer l'état d'une candidature")
    print(f"  6. 📝 Ajouter une note")
    print(f"  7. 🧹 Nettoyer offres")
    print(f"  8. 🚪 Quitter")
    print(f"{'='*50}")


def voir_candidatures():
    candidatures = charger_suivi()
    if not candidatures:
        print("  Aucune candidature. Importe d'abord les offres (option 1).")
        return

    candidatures.sort(key=lambda c: c.score or 0, reverse=True)
    print(f"\n  {len(candidatures)} candidatures :\n")
    for i, c in enumerate(candidatures):
        print(f"    {i+1}. {c.résumé()}")


def voir_relances():
    candidatures = charger_suivi()
    a_relancer = [c for c in candidatures if c.doit_relancer()]

    if not a_relancer:
        print("  ✅ Aucune relance à faire pour le moment !")
        return

    print(f"\n  🔔 {len(a_relancer)} candidature(s) à relancer :\n")
    for c in a_relancer:
        print(f"    {c.résumé()}")
        print(f"      → Date relance prévue : {c.date_relance[:10]}")


def changer_etat():
    candidatures = charger_suivi()
    if not candidatures:
        print("  Aucune candidature.")
        return

    candidatures.sort(key=lambda c: c.score or 0, reverse=True)
    for i, c in enumerate(candidatures):
        print(f"    {i+1}. {c.résumé()}")

    try:
        choix = int(input("\n  Numéro de la candidature : ")) - 1
        if choix < 0 or choix >= len(candidatures):
            print("  ⚠️  Numéro invalide")
            return
    except ValueError:
        print("  ⚠️  Saisie invalide")
        return

    c = candidatures[choix]
    print(f"\n  Sélectionné : {c.titre} @ {c.entreprise} [{c.etat}]")

    print(f"  États disponibles :")
    for etat, emoji in ETATS.items():
        print(f"    - {etat} {emoji}")

    nouvel_etat = input("\n  Nouvel état : ").strip().lower()
    commentaire = input("  Commentaire (optionnel) : ").strip()

    c.changer_etat(nouvel_etat, commentaire)
    sauvegarder_suivi(candidatures)
    print(f"  ✅ État mis à jour : {c.résumé()}")


def ajouter_note():
    candidatures = charger_suivi()
    if not candidatures:
        print("  Aucune candidature.")
        return

    for i, c in enumerate(candidatures):
        print(f"    {i+1}. {c.résumé()}")

    try:
        choix = int(input("\n  Numéro de la candidature : ")) - 1
        if choix < 0 or choix >= len(candidatures):
            print("  ⚠️  Numéro invalide")
            return
    except ValueError:
        print("  ⚠️  Saisie invalide")
        return

    c = candidatures[choix]
    note = input("  Note : ").strip()
    if note:
        c.ajouter_note(note)
        sauvegarder_suivi(candidatures)
        print(f"  ✅ Note ajoutée à {c.entreprise}")


def menu_nettoyage():
    """Sous-menu nettoyage — print() pour l'UI, log pour les opérations."""
    print(f"\n  🧹 NETTOYAGE DES OFFRES")
    print(f"  {'─'*40}")
    print(f"  Une sauvegarde est créée automatiquement.\n")
    print(f"    a. Supprimer les offres déjà dans le suivi")
    print(f"    b. Supprimer seulement les offres refusées")
    print(f"    c. Supprimer les offres terminées (acceptées + refusées)")
    print(f"    d. 🔍 Détecter les doublons (simulation)")
    print(f"    e. 🧹 Supprimer les doublons")
    print(f"    f. 💀 Purger les offres demo + réinitialiser le suivi")
    print(f"    g. 📦 Archiver les offres sous le seuil")
    print(f"    q. Annuler\n")

    choix = input("  Ton choix : ").strip().lower()

    modes = {"a": "traitees", "b": "refusees", "c": "terminees"}
    if choix in modes:
        mode = modes[choix]
        labels = {
            "traitees": "toutes les offres déjà dans le suivi",
            "refusees": "les offres refusées uniquement",
            "terminees": "les offres acceptées et refusées",
        }
        print(f"\n  ⚠️  Tu vas supprimer {labels[mode]} de offres.json.")
        confirm = input("  Confirmer ? (oui/non) : ").strip().lower()
        if confirm in ("oui", "o", "yes", "y"):
            nettoyer_offres(mode=mode)
        else:
            print("  ↩️  Annulé.")
    elif choix == "d":
        print(f"\n  🔍 Analyse des doublons (aucune modification)...\n")
        dedupliquer_offres(dry_run=True)
    elif choix == "e":
        print(f"\n  🔍 Doublons détectés :\n")
        result = dedupliquer_offres(dry_run=True)
        total = result["doublons_id"] + result["doublons_titre"]
        if total == 0:
            return
        print(f"\n  ⚠️  {total} doublons seront supprimés de offres.json.")
        confirm = input("  Confirmer ? (oui/non) : ").strip().lower()
        if confirm in ("oui", "o", "yes", "y"):
            dedupliquer_offres(dry_run=False)
        else:
            print("  ↩️  Annulé.")
    elif choix == "f":
        print(f"\n  ⚠️  Cette action va :")
        print(f"     1. Supprimer TOUTES les offres demo de offres.json")
        print(f"     2. Vider complètement suivi.json")
        print(f"     Des sauvegardes seront créées automatiquement.\n")
        confirm = input("  Confirmer ? (oui/non) : ").strip().lower()
        if confirm in ("oui", "o", "yes", "y"):
            purger_offres_demo()
            reinitialiser_suivi()
            print(f"\n  ✅ Base nettoyée. Tu peux relancer le scoring sur les offres WTTJ réelles.")
        else:
            print("  ↩️  Annulé.")
    elif choix == "g":
        try:
            seuil_input = input("  Seuil minimum (défaut = 60) : ").strip()
            seuil = int(seuil_input) if seuil_input else 60
        except ValueError:
            seuil = 60
        archiver_offres_sous_seuil(score_minimum=seuil)
    elif choix == "q":
        print("  ↩️  Annulé.")
    else:
        print("  ⚠️  Choix invalide.")


def lancer_suivi():
    """Boucle principale du menu interactif."""
    print("\n🚀 Agent Alternance — Module de Suivi")
    log.info("Module de suivi démarré")

    while True:
        afficher_menu()
        choix = input("  Ton choix : ").strip()

        if choix == "1":
            importer_offres_qualifiees(score_minimum=60)
        elif choix == "2":
            candidatures = charger_suivi()
            generer_dashboard(candidatures)
        elif choix == "3":
            voir_candidatures()
        elif choix == "4":
            voir_relances()
        elif choix == "5":
            changer_etat()
        elif choix == "6":
            ajouter_note()
        elif choix == "7":
            menu_nettoyage()
        elif choix == "8":
            print("\n  👋 À bientôt !\n")
            log.info("Module de suivi arrêté")
            break
        else:
            print("  ⚠️  Choix invalide")


if __name__ == "__main__":
    lancer_suivi()
