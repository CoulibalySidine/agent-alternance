"""
indeed.py — Scraper pour Indeed.fr (v3)
========================================

V3 — Migration vers logger.
Le retry et le backoff sont hérités de BaseScraper.requeter().
"""

from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import Offre
from logger import get_logger

log = get_logger("sourcing.indeed")


class IndeedScraper(BaseScraper):
    """Scraper spécialisé pour Indeed.fr"""

    NOM = "indeed"
    BASE_URL = "https://fr.indeed.com"
    RESULTATS_PAR_PAGE = 10

    def construire_url(self, page: int = 1) -> str:
        offset = (page - 1) * self.RESULTATS_PAR_PAGE
        mot_cle_encode = quote_plus(self.mot_cle)
        ville_encodee = quote_plus(self.ville)
        return (
            f"{self.BASE_URL}/jobs"
            f"?q={mot_cle_encode}"
            f"&l={ville_encodee}"
            f"&start={offset}"
        )

    def extraire_offres(self, soup: BeautifulSoup) -> list[Offre]:
        offres = []
        cartes = soup.find_all("div", class_="job_seen_beacon")

        for carte in cartes:
            try:
                titre_elem = carte.find("h2", class_="jobTitle")
                if not titre_elem:
                    continue
                titre = titre_elem.get_text(strip=True)

                lien_elem = titre_elem.find("a", href=True)
                url = self.BASE_URL + lien_elem["href"] if lien_elem else ""

                entreprise_elem = carte.find("span", attrs={"data-testid": "company-name"})
                entreprise = entreprise_elem.get_text(strip=True) if entreprise_elem else "Non précisé"

                lieu_elem = carte.find("div", attrs={"data-testid": "text-location"})
                lieu = lieu_elem.get_text(strip=True) if lieu_elem else "Non précisé"

                desc_elem = carte.find("div", class_="css-9446fg")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                offre = Offre(
                    titre=titre, entreprise=entreprise, url=url,
                    source=self.NOM, lieu=lieu, description=description,
                )
                offres.append(offre)

            except Exception as e:
                log.warning(f"Erreur sur une carte : {e}")
                continue

        return offres

    def a_page_suivante(self, soup: BeautifulSoup, page_actuelle: int) -> bool:
        if page_actuelle >= 5:
            return False
        bouton_suivant = soup.find("a", attrs={"aria-label": "Next Page"})
        return bouton_suivant is not None
