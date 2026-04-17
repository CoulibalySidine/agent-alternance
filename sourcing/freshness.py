"""
freshness.py — Rafraîchissement et nettoyage des offres
=========================================================

Fonctions utilitaires pour :
- Calculer l'âge d'une offre en jours
- Vérifier si une URL est encore active (HEAD request)
- Supprimer les offres périmées en batch

Utilisé par api/routes/sourcing.py
"""

import requests
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from sourcing.models import Offre
from logger import get_logger

log = get_logger("sourcing.freshness")


def age_en_jours(offre: Offre) -> int:
    """Calcule l'âge d'une offre en jours depuis sa collecte."""
    try:
        date = datetime.fromisoformat(offre.date_collecte)
        delta = datetime.now() - date
        return delta.days
    except (ValueError, TypeError):
        return 0


def verifier_url(url: str, timeout: int = 8) -> dict:
    """
    Vérifie si une URL est encore accessible.

    Returns:
        {"url": "...", "status": 200, "actif": True}
        {"url": "...", "status": 404, "actif": False}
        {"url": "...", "status": -1, "actif": False, "erreur": "timeout"}
    """
    if not url or url.startswith("https://demo.local"):
        return {"url": url, "status": -1, "actif": True, "erreur": "non vérifiable"}

    try:
        resp = requests.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )
        actif = resp.status_code < 400
        return {"url": url, "status": resp.status_code, "actif": actif}

    except requests.exceptions.Timeout:
        return {"url": url, "status": -1, "actif": False, "erreur": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"url": url, "status": -1, "actif": False, "erreur": "connexion impossible"}
    except Exception as e:
        return {"url": url, "status": -1, "actif": False, "erreur": str(e)}


def verifier_offres_batch(offres: list[Offre], max_workers: int = 5) -> list[dict]:
    """
    Vérifie les URLs de plusieurs offres en parallèle.

    Returns:
        [{"offre_id": "...", "titre": "...", "age_jours": 12, "url_active": True, "status": 200}, ...]
    """
    resultats = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for offre in offres:
            future = executor.submit(verifier_url, offre.url)
            futures[future] = offre

        for future in as_completed(futures):
            offre = futures[future]
            try:
                check = future.result()
                resultats.append({
                    "offre_id": offre.id,
                    "titre": offre.titre,
                    "entreprise": offre.entreprise,
                    "age_jours": age_en_jours(offre),
                    "url_active": check["actif"],
                    "status": check["status"],
                    "erreur": check.get("erreur"),
                })
            except Exception as e:
                resultats.append({
                    "offre_id": offre.id,
                    "titre": offre.titre,
                    "entreprise": offre.entreprise,
                    "age_jours": age_en_jours(offre),
                    "url_active": False,
                    "status": -1,
                    "erreur": str(e),
                })

    return resultats


def stats_fraicheur(offres: list[Offre]) -> dict:
    """
    Calcule des statistiques de fraîcheur sur les offres.

    Returns:
        {
            "total": 42,
            "moins_de_7j": 15,
            "7_a_14j": 12,
            "14_a_30j": 10,
            "plus_de_30j": 5,
            "age_moyen": 11.3,
            "par_source": {"wttj": 20, "lba": 22},
        }
    """
    if not offres:
        return {"total": 0}

    ages = [age_en_jours(o) for o in offres]
    par_source = {}
    for o in offres:
        par_source[o.source] = par_source.get(o.source, 0) + 1

    return {
        "total": len(offres),
        "moins_de_7j": sum(1 for a in ages if a < 7),
        "7_a_14j": sum(1 for a in ages if 7 <= a < 14),
        "14_a_30j": sum(1 for a in ages if 14 <= a < 30),
        "plus_de_30j": sum(1 for a in ages if a >= 30),
        "age_moyen": round(sum(ages) / len(ages), 1) if ages else 0,
        "par_source": par_source,
    }
