"""
runner.py — Orchestrateur de la collecte (v3)
==============================================

V3 — Migration vers logger.
"""

from .models import Offre, sauvegarder_offres, charger_offres, dédupliquer
from .scrapers.base import BaseScraper
from .scrapers.demo import DemoScraper
from .scrapers.wttj import WttjScraper

from logger import get_logger

log = get_logger("sourcing")


def lancer_collecte(
    mot_cle: str = "alternance développeur",
    ville: str = "Paris",
    max_pages: int = 3,
    mode_demo: bool = False,
) -> list[Offre]:
    """Lance la collecte sur toutes les plateformes."""

    log.info(f"{'='*50}")
    log.info(f"🚀 SOURCING — '{mot_cle}' à {ville}")
    log.info(f"   Max {max_pages} pages — Mode {'DEMO' if mode_demo else 'PRODUCTION'}")
    log.info(f"{'='*50}")

    scrapers: list[BaseScraper] = []

    if mode_demo:
        scrapers.append(DemoScraper(mot_cle, ville, nb_offres=12))
    else:
        scrapers.append(WttjScraper(mot_cle, ville))

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
