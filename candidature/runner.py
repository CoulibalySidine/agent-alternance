"""
runner.py — Orchestrateur du module Candidature (v4)
=====================================================

V4 — Suppression de sys.path.insert (utilise pyproject.toml),
     noms de fichiers safe pour les accents.
"""

import os
import time
from pathlib import Path

from sourcing.models import charger_offres
from candidature.generateur import Generateur, nom_fichier_safe
from candidature.cv_adapter import CVAdapter
from candidature.fiche_entretien import FicheEntretien
from candidature.reponses_questions import ReponsesQuestions
from logger import get_logger

log = get_logger("candidature")

OUTPUT_BASE = Path(__file__).parent / "lettres"


def lancer_candidature(
    api_key: str = "",
    score_minimum: int = 60,
    max_dossiers: int = 3,
    questions_custom: list[str] = None,
):
    """Génère un dossier complet par offre qualifiée."""

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("Clé API manquante ! Ajoute ANTHROPIC_API_KEY dans .env")
        return

    offres = charger_offres()
    if not offres:
        log.error("Aucune offre. Lance d'abord sourcing puis qualification.")
        return

    qualifiees = [o for o in offres if o.score is not None and o.score >= score_minimum]
    qualifiees.sort(key=lambda o: o.score, reverse=True)

    if not qualifiees:
        log.error(f"Aucune offre avec score ≥ {score_minimum}")
        return

    a_traiter = qualifiees[:max_dossiers]

    # Résumé de démarrage (print = UI pour l'utilisateur)
    print(f"\n{'='*60}")
    print(f"📁 CANDIDATURE — Génération de dossiers complets")
    print(f"{'='*60}")
    print(f"   Offres qualifiées (score ≥ {score_minimum}) : {len(qualifiees)}")
    print(f"   Dossiers à générer : {len(a_traiter)}")
    print(f"   Contenu : CV + Lettre + Fiche entretien + Réponses formulaire")
    print(f"{'='*60}")

    log.info(f"Génération de {len(a_traiter)} dossiers (score ≥ {score_minimum})")

    generateur_lettre = Generateur(api_key=api_key)
    adaptateur_cv = CVAdapter(api_key=api_key)
    generateur_fiche = FicheEntretien(api_key=api_key)
    generateur_reponses = ReponsesQuestions(api_key=api_key)

    resultats = []

    for i, offre in enumerate(a_traiter):
        offre_dict = offre.to_dict()
        entreprise = offre.entreprise
        titre = offre.titre
        score = offre.score

        print(f"\n{'─'*60}")
        print(f"📁 [{i+1}/{len(a_traiter)}] {titre} @ {entreprise} (score: {score})")
        print(f"{'─'*60}")

        log.info(f"[{i+1}/{len(a_traiter)}] Dossier : {titre} @ {entreprise} (score: {score})")

        nom_dossier = nom_fichier_safe(entreprise, max_len=40)
        dossier = OUTPUT_BASE / nom_dossier
        dossier.mkdir(parents=True, exist_ok=True)

        resultat = {
            "entreprise": entreprise, "titre": titre, "score": score,
            "dossier": str(dossier), "cv": None, "lettre_docx": None,
            "lettre_pdf": None, "fiche": None, "reponses": None,
        }

        # 1. CV Adapté
        try:
            chemin_cv = adaptateur_cv.generer_cv(offre_dict, dossier)
            resultat["cv"] = str(chemin_cv) if chemin_cv else None
        except Exception as e:
            log.warning(f"Erreur CV : {e}")

        time.sleep(1)

        # 2. Lettre de motivation
        try:
            res_lettre = generateur_lettre.generer_pour_offre(offre_dict)
            if res_lettre:
                for ext in ("docx", "pdf", "txt"):
                    ancien = res_lettre.get(ext)
                    if ancien and Path(ancien).exists():
                        nouveau = dossier / Path(ancien).name
                        Path(ancien).rename(nouveau)
                        resultat[f"lettre_{ext}" if ext != "txt" else "lettre_txt"] = str(nouveau)
        except Exception as e:
            log.warning(f"Erreur lettre : {e}")

        time.sleep(1)

        # 3. Fiche entretien
        try:
            chemin_fiche = generateur_fiche.sauvegarder_fiche(offre_dict, dossier)
            resultat["fiche"] = str(chemin_fiche) if chemin_fiche else None
        except Exception as e:
            log.warning(f"Erreur fiche : {e}")

        time.sleep(1)

        # 4. Réponses formulaire
        try:
            chemin_reponses = generateur_reponses.sauvegarder_reponses(
                offre_dict, dossier, questions_custom=questions_custom
            )
            resultat["reponses"] = str(chemin_reponses) if chemin_reponses else None
        except Exception as e:
            log.warning(f"Erreur réponses : {e}")

        resultats.append(resultat)

    # Résumé final (print = UI pour l'utilisateur)
    print(f"\n{'='*60}")
    print(f"📊 RÉSUMÉ — {len(resultats)} dossiers générés")
    print(f"{'='*60}\n")

    for r in resultats:
        print(f"  📁 {r['entreprise']} — {r['titre']} (score: {r['score']})")
        print(f"     Dossier : {r['dossier']}")
        print(f"     {'✅' if r.get('cv') else '❌'} CV adapté")
        print(f"     {'✅' if r.get('lettre_docx') else '❌'} Lettre de motivation")
        print(f"     {'✅' if r.get('fiche') else '❌'} Fiche entretien")
        print(f"     {'✅' if r.get('reponses') else '❌'} Réponses formulaire")
        print()

    log.info(f"Terminé : {len(resultats)} dossiers générés")

    print(f"{'='*60}")
    print(f"💡 Ouvre candidature/lettres/ pour voir tes dossiers !")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    from config import env

    lancer_candidature(
        api_key=env("ANTHROPIC_API_KEY", ""),
        score_minimum=60,
        max_dossiers=3,
    )
