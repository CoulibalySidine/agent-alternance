"""
runner.py — Orchestrateur du module Qualification
==================================================

CONCEPT CLÉ : pipeline en chaîne.

Ce runner :
1. Charge les offres collectées par le module Sourcing
2. Filtre celles qui n'ont pas encore été scorées
3. Envoie chaque offre à l'API Claude pour scoring
4. Sauvegarde les résultats dans offres.json (même fichier)
5. Affiche un classement

Le fichier offres.json est PARTAGÉ entre Sourcing et Qualification.
Le champ "score" passe de null (après sourcing) à un nombre (après qualification).
"""

import os

from sourcing.models import Offre, charger_offres, sauvegarder_offres
from qualification.scorer import Scorer
from logger import get_logger

log = get_logger("qualification")


def lancer_qualification(
    api_key: str = "",
    score_minimum: int = 0,
    max_offres: int = 0,
    forcer_rescore: bool = False,
) -> list[Offre]:
    """
    Lance le scoring de toutes les offres non encore évaluées.

    Args:
        api_key: clé API Anthropic. Si vide, cherche dans
                 la variable d'environnement ANTHROPIC_API_KEY.
        score_minimum: ne garder que les offres au-dessus de ce score.
        max_offres: limiter le nombre d'offres à scorer (0 = toutes).
                    Utile pour tester sans consommer trop de tokens.
        forcer_rescore: si True, re-score même les offres déjà évaluées.

    Returns:
        Liste d'offres scorées et triées.
    """
    # --- Récupérer la clé API ---
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("Clé API Anthropic manquante !")
        print("❌ Clé API Anthropic manquante !")
        print("   Deux options :")
        print("   1. Fichier .env : ANTHROPIC_API_KEY=sk-ant-...")
        print("   2. Variable d'environnement : export ANTHROPIC_API_KEY=sk-ant-...")
        return []

    # --- Charger les offres ---
    offres = charger_offres()
    if not offres:
        log.warning("Aucune offre en base")
        print("❌ Aucune offre en base. Lance d'abord le module Sourcing :")
        print("   python -m sourcing.runner")
        return []

    log.info(f"{len(offres)} offres chargées depuis offres.json")
    print(f"\n📦 {len(offres)} offres chargées depuis offres.json")

    # --- Filtrer les offres à scorer ---
    if forcer_rescore:
        a_scorer = offres
        log.info(f"Mode rescore : {len(a_scorer)} offres seront réévaluées")
        print(f"   🔄 Mode rescore : toutes les {len(a_scorer)} offres seront réévaluées")
    else:
        a_scorer = [o for o in offres if o.score is None]
        deja_scorees = len(offres) - len(a_scorer)
        log.info(f"{deja_scorees} déjà scorées, {len(a_scorer)} à évaluer")
        print(f"   ✅ {deja_scorees} déjà scorées, {len(a_scorer)} à évaluer")

    if not a_scorer:
        print("   🎉 Toutes les offres sont déjà scorées !")
        offres_triees = sorted(offres, key=lambda o: o.score or 0, reverse=True)
        _afficher_classement(offres_triees)
        return offres_triees

    # --- Limiter si demandé ---
    if max_offres > 0 and len(a_scorer) > max_offres:
        log.info(f"Limité à {max_offres} offres (sur {len(a_scorer)})")
        print(f"   📎 Limité à {max_offres} offres (sur {len(a_scorer)})")
        a_scorer = a_scorer[:max_offres]

    # --- Scorer ---
    scorer = Scorer(api_key=api_key)

    # Convertir en dicts pour le scorer
    offres_dicts = [o.to_dict() for o in a_scorer]
    resultats = scorer.scorer_offres(offres_dicts, score_minimum=0)

    # --- Mettre à jour les offres avec TOUS les résultats du scoring ---
    index_offres = {o.id: o for o in offres}

    for resultat in resultats:
        offre_id = resultat.get("id", "")
        if offre_id in index_offres:
            offre = index_offres[offre_id]
            offre.score = resultat.get("score")
            # Récupérer TOUTES les données d'analyse (avant : perdues)
            offre.raison_score = resultat.get("raison_score", "")
            offre.points_forts = resultat.get("points_forts", [])
            offre.points_faibles = resultat.get("points_faibles", [])
            offre.conseil = resultat.get("conseil", "")

    log.info(f"{len(resultats)} offres scorées avec succès")

    # --- Sauvegarder ---
    sauvegarder_offres(offres)

    # --- Classement final ---
    offres_triees = sorted(offres, key=lambda o: o.score or 0, reverse=True)

    if score_minimum > 0:
        offres_triees = [o for o in offres_triees if (o.score or 0) >= score_minimum]
        log.info(f"{len(offres_triees)} offres avec score ≥ {score_minimum}")
        print(f"\n🔍 {len(offres_triees)} offres avec score ≥ {score_minimum}")

    _afficher_classement(offres_triees)

    return offres_triees


def _afficher_classement(offres: list[Offre]):
    """Affiche le classement des offres scorées."""
    scorees = [o for o in offres if o.score is not None]
    if not scorees:
        return

    print(f"\n{'='*60}")
    print(f"🏆 CLASSEMENT FINAL — {len(scorees)} offres évaluées")
    print(f"{'='*60}\n")

    for i, offre in enumerate(scorees[:10]):
        emoji = "🟢" if offre.score >= 70 else "🟡" if offre.score >= 40 else "🔴"
        rang = f"#{i+1}".ljust(4)
        score = f"{offre.score}/100"
        print(f"  {rang} {emoji} {score}  {offre.titre}")
        print(f"         📍 {offre.entreprise} — {offre.lieu}")

    if len(scorees) > 10:
        print(f"\n  ... et {len(scorees) - 10} autres offres")


# --- Point d'entrée direct ---
if __name__ == "__main__":
    # La clé API vient du fichier .env ou de la variable d'environnement
    # PLUS JAMAIS de clé en dur ici !
    from config import env

    lancer_qualification(
        api_key=env("ANTHROPIC_API_KEY", ""),
        max_offres=5,  # Commence par 5 pour tester (économise les tokens)
    )
