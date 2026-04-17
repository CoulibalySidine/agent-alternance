"""
runner.py — Orchestrateur de la collecte (v4)
==============================================

V4 — Ajout du scraper La bonne alternance (API officielle).
     Sélection de source(s) via paramètre.
"""

from .models import Offre, sauvegarder_offres, charger_offres, dédupliquer
from .scrapers.base import BaseScraper
from .scrapers.demo import DemoScraper
from .scrapers.wttj import WttjScraper
from .scrapers.lba import LbaScraper

from logger import get_logger

log = get_logger("sourcing")

# Sources disponibles
SOURCES_DISPONIBLES = {
    "wttj": "Welcome to the Jungle (Algolia)",
    "lba": "La bonne alternance (France Travail + partenaires)",
    "demo": "Données de démonstration",
}


def lancer_collecte(
    mot_cle: str = "alternance développeur",
    ville: str = "Paris",
    max_pages: int = 3,
    mode_demo: bool = False,
    sources: list[str] = None,
) -> list[Offre]:
    """
    Lance la collecte sur les plateformes sélectionnées.

    Args:
        mot_cle: Mots-clés de recherche
        ville: Ville de recherche
        max_pages: Pages max par scraper (pour WTTJ)
        mode_demo: Utiliser le scraper démo
        sources: Liste des sources à utiliser. None = toutes.
                 Options : "wttj", "lba", "demo"
    """
    log.info(f"{'='*50}")
    log.info(f"🚀 SOURCING — '{mot_cle}' à {ville}")
    log.info(f"   Max {max_pages} pages — Mode {'DEMO' if mode_demo else 'PRODUCTION'}")
    log.info(f"{'='*50}")

    scrapers: list[BaseScraper] = []

    if mode_demo:
        scrapers.append(DemoScraper(mot_cle, ville, nb_offres=12))
    else:
        # Déterminer les sources à utiliser
        if sources is None:
            # Par défaut : WTTJ + LBA
            sources_actives = ["wttj", "lba"]
        else:
            sources_actives = [s.lower().strip() for s in sources if s]

        for source in sources_actives:
            if source == "wttj":
                scrapers.append(WttjScraper(mot_cle, ville))
            elif source == "lba":
                scrapers.append(LbaScraper(mot_cle, ville))
            elif source == "demo":
                scrapers.append(DemoScraper(mot_cle, ville, nb_offres=12))
            else:
                log.warning(f"Source inconnue ignorée : {source}")

    if not scrapers:
        log.warning("Aucun scraper configuré — rien à collecter")
        return charger_offres()

    log.info(f"   Sources : {', '.join(s.NOM for s in scrapers)}")

    nouvelles_offres: list[Offre] = []

    for scraper in scrapers:
        try:
            offres = scraper.collecter(max_pages=max_pages)
            nouvelles_offres.extend(offres)
        except Exception as e:
            log.error(f"Erreur avec {scraper.NOM} : {e}")
            continue

    existantes = charger_offres()
    uniques = dédupliquer(nouvelles_offres, existantes)

    toutes = existantes + uniques
    sauvegarder_offres(toutes)

    log.info(f"{'='*50}")
    log.info(f"📊 RÉSUMÉ DE LA COLLECTE")
    log.info(f"   Nouvelles collectées : {len(nouvelles_offres)}")
    log.info(f"   Doublons ignorés     : {len(nouvelles_offres) - len(uniques)}")
    log.info(f"   Ajoutées             : {len(uniques)}")
    log.info(f"   Total en base        : {len(toutes)}")
    log.info(f"{'='*50}")

    if uniques:
        log.info("📌 Aperçu des nouvelles offres :")
        for offre in uniques[:5]:
            log.info(f"   {offre.résumé()}")
        if len(uniques) > 5:
            log.info(f"   ... et {len(uniques) - 5} autres")

    return toutes


if __name__ == "__main__":
    lancer_collecte(mode_demo=False)
