"""
wttj.py — Scraper Welcome to the Jungle via Algolia API (v3)
==============================================================

V3 — Migration vers logger.
"""

import json
import time
import random
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import Offre
from logger import get_logger

try:
    import requests
except ImportError:
    raise ImportError("pip install requests")

log = get_logger("sourcing.wttj")


class WttjScraper(BaseScraper):
    """Scraper WTTJ via l'API Algolia."""

    NOM = "wttj"

    ALGOLIA_APP_ID = "CSEKHVMS53"
    ALGOLIA_API_KEY = "4bd8f6215d0cc52b26430765769e65a0"
    ALGOLIA_INDEX = "wttj_jobs_production_fr"

    RESULTATS_PAR_PAGE = 20
    BASE_URL = "https://www.welcometothejungle.com/fr/jobs"

    def __init__(self, mot_cle: str = "alternance développeur", ville: str = "Paris"):
        super().__init__(mot_cle, ville)

        if self.ALGOLIA_APP_ID == "CHANGE_MOI":
            raise ValueError(
                "❌ Tu n'as pas encore rempli les clés Algolia !\n"
                "   Ouvre sourcing/scrapers/wttj.py et remplace CHANGE_MOI\n"
                "   par les valeurs trouvées dans Chrome DevTools."
            )

        self.algolia_url = (
            f"https://{self.ALGOLIA_APP_ID}-dsn.algolia.net"
            f"/1/indexes/*/queries"
        )

        self.session.headers.update({
            "x-algolia-application-id": self.ALGOLIA_APP_ID,
            "x-algolia-api-key": self.ALGOLIA_API_KEY,
            "Content-Type": "application/json",
            "Referer": "https://www.welcometothejungle.com/",
            "Origin": "https://www.welcometothejungle.com",
        })

    def construire_url(self, page: int = 1) -> str:
        return self.algolia_url

    def requeter(self, url: str, tentative: int = 1):
        """POST vers Algolia avec retry et backoff."""
        params = (
            f"query={self.mot_cle}"
            f"&page={self._page_courante}"
            f"&hitsPerPage={self.RESULTATS_PAR_PAGE}"
        )

        body = {
            "requests": [
                {
                    "indexName": self.ALGOLIA_INDEX,
                    "params": params,
                }
            ]
        }

        try:
            label = f"(tentative {tentative}/{self.MAX_RETRIES})" if tentative > 1 else ""
            log.debug(f"POST {url[:60]} (page {self._page_courante}) {label}")
            response = self.session.post(url, json=body, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if "results" in data and len(data["results"]) > 0:
                    return data["results"][0]
                return data

            if response.status_code == 429:
                return self._retry_ou_abandon(url, tentative, raison="Rate limit Algolia (429)", forcer_retry=True)

            if response.status_code >= 500:
                return self._retry_ou_abandon(url, tentative, raison=f"Erreur serveur Algolia ({response.status_code})")

            if response.status_code == 403:
                return self._retry_ou_abandon(url, tentative, raison="Accès refusé (403) — clés Algolia expirées ?", max_retry_override=2)

            log.warning(f"Code HTTP {response.status_code}")
            self._enregistrer_erreur(f"HTTP {response.status_code}", url)
            return None

        except requests.Timeout:
            return self._retry_ou_abandon(url, tentative, raison="Timeout Algolia")
        except requests.ConnectionError:
            return self._retry_ou_abandon(url, tentative, raison="Erreur de connexion")
        except Exception as e:
            log.error(f"Erreur : {e}")
            self._enregistrer_erreur(str(e), url)
            return None

    def extraire_offres(self, soup) -> list[Offre]:
        """Extrait les offres depuis la réponse JSON d'Algolia."""
        data = soup

        if not data or "hits" not in data:
            return []

        self._nb_pages_total = data.get("nbPages", 1)
        self._nb_hits_total = data.get("nbHits", 0)

        offres = []

        for hit in data["hits"]:
            try:
                titre = hit.get("name", "Sans titre")

                org = hit.get("organization", {}) or {}
                entreprise = org.get("name", "Non précisé")
                org_slug = org.get("slug", "")

                offices = hit.get("offices") or []
                if offices:
                    premier_bureau = offices[0]
                    ville = premier_bureau.get("local_city") or premier_bureau.get("city", "Non précisé")
                    pays = premier_bureau.get("country", "")
                    lieu = f"{ville}, {pays}" if pays and pays != "France" else ville
                else:
                    lieu = "Non précisé"

                slug = hit.get("slug", "")
                url = f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}" if slug and org_slug else ""

                description = hit.get("summary") or ""
                missions = hit.get("key_missions") or []
                if missions:
                    missions_txt = " | ".join(missions)
                    description = f"{description} Missions : {missions_txt}" if description else missions_txt
                if len(description) > 500:
                    description = description[:500] + "..."

                contrat_raw = hit.get("contract_type", "")
                contrat_map = {
                    "apprenticeship": "Alternance", "internship": "Stage",
                    "full_time": "CDI", "part_time": "Temps partiel",
                    "temporary": "CDD", "freelance": "Freelance", "vie": "VIE",
                }
                type_contrat = contrat_map.get(contrat_raw, contrat_raw or "Alternance")

                salaire_min = hit.get("salary_minimum")
                salaire_max = hit.get("salary_maximum")
                salaire_devise = hit.get("salary_currency", "EUR")
                salaire_periode = hit.get("salary_period", "")
                salaire = None
                if salaire_min and salaire_max:
                    salaire = f"{salaire_min} - {salaire_max} {salaire_devise} / {salaire_periode}"
                elif salaire_min:
                    salaire = f"{salaire_min}+ {salaire_devise} / {salaire_periode}"

                date_pub = hit.get("published_at_date", "") or ""

                offre = Offre(
                    titre=titre, entreprise=entreprise, url=url,
                    source=self.NOM, lieu=lieu, description=description,
                    type_contrat=type_contrat, salaire=salaire,
                    date_publication=date_pub,
                )
                offres.append(offre)

            except Exception as e:
                log.warning(f"Erreur sur un hit : {e}")
                continue

        return offres

    def a_page_suivante(self, soup, page_actuelle: int) -> bool:
        if page_actuelle >= 5:
            return False
        return self._page_courante < self._nb_pages_total - 1

    def collecter(self, max_pages: int = 3) -> list[Offre]:
        """Override pour la pagination Algolia (base 0)."""
        log.info(f"{'='*50}")
        log.info(f"🌴 WTTJ — '{self.mot_cle}' à {self.ville}")
        log.info(f"{'='*50}")

        self._stats = {"pages_ok": 0, "pages_erreur": 0, "retries_total": 0, "erreurs": []}
        toutes_offres: list[Offre] = []
        echecs_consecutifs = 0

        for page in range(max_pages):
            self._page_courante = page
            log.info(f"📄 Page {page + 1}/{max_pages}")

            url = self.construire_url(page + 1)
            data = self.requeter(url)

            if data is None:
                echecs_consecutifs += 1
                if echecs_consecutifs >= 2:
                    log.error("Arrêt : 2 échecs consécutifs — Algolia inaccessible")
                    break
                log.warning("Page ignorée — on tente la suivante")
                continue

            echecs_consecutifs = 0
            self._stats["pages_ok"] += 1

            offres_page = self.extraire_offres(data)
            log.info(f"✅ {len(offres_page)} offres trouvées")

            if not offres_page:
                log.info("Aucune offre — dernière page atteinte")
                break

            toutes_offres.extend(offres_page)

            if not self.a_page_suivante(data, page + 1):
                log.info(f"Dernière page ({self._nb_hits_total} offres au total sur WTTJ)")
                break

            if page < max_pages - 1:
                self.attendre()

        self._afficher_resume(toutes_offres)
        return toutes_offres
