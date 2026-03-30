"""
base.py — Classe de base pour tous les scrapers (v3)
=====================================================

V3 — Migration vers logger (plus de print() sauf UI).
"""

import time
import random
from abc import ABC, abstractmethod
from typing import Optional
from bs4 import BeautifulSoup

try:
    import requests
except ImportError:
    raise ImportError(
        "❌ Le module 'requests' est requis.\n"
        "   Installe-le avec : pip install requests beautifulsoup4"
    )

from ..models import Offre
from logger import get_logger

log = get_logger("sourcing.base")


class BaseScraper(ABC):
    """
    Classe abstraite = un "plan" que les scrapers enfants doivent suivre.
    """

    NOM: str = "base"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    DELAI_MIN: float = 1.0
    DELAI_MAX: float = 3.0
    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 2.0

    def __init__(self, mot_cle: str = "alternance développeur", ville: str = "Paris"):
        self.mot_cle = mot_cle
        self.ville = ville
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._stats = {
            "pages_ok": 0,
            "pages_erreur": 0,
            "retries_total": 0,
            "erreurs": [],
        }

    # =========================================================================
    # MÉTHODES ABSTRAITES
    # =========================================================================

    @abstractmethod
    def construire_url(self, page: int = 1) -> str:
        pass

    @abstractmethod
    def extraire_offres(self, soup: BeautifulSoup) -> list[Offre]:
        pass

    @abstractmethod
    def a_page_suivante(self, soup: BeautifulSoup, page_actuelle: int) -> bool:
        pass

    # =========================================================================
    # MÉTHODES COMMUNES (v3 — avec logger)
    # =========================================================================

    def requeter(self, url: str, tentative: int = 1) -> Optional[BeautifulSoup]:
        """Envoie une requête HTTP avec retry et backoff."""
        try:
            label = f"(tentative {tentative}/{self.MAX_RETRIES})" if tentative > 1 else ""
            log.debug(f"GET {url[:80]} {label}")
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")

            if response.status_code == 429:
                return self._retry_ou_abandon(url, tentative, raison="Rate limit (429)", forcer_retry=True)

            if response.status_code >= 500:
                return self._retry_ou_abandon(url, tentative, raison=f"Erreur serveur ({response.status_code})")

            if response.status_code == 403:
                return self._retry_ou_abandon(url, tentative, raison="Accès refusé (403)", max_retry_override=2)

            log.warning(f"Code HTTP {response.status_code} — page ignorée")
            self._enregistrer_erreur(f"HTTP {response.status_code}", url)
            return None

        except requests.Timeout:
            return self._retry_ou_abandon(url, tentative, raison="Timeout")
        except requests.ConnectionError:
            return self._retry_ou_abandon(url, tentative, raison="Erreur de connexion")
        except requests.RequestException as e:
            log.error(f"Erreur inattendue : {e}")
            self._enregistrer_erreur(str(e), url)
            return None

    def _retry_ou_abandon(self, url, tentative, raison, forcer_retry=False, max_retry_override=None):
        """Décide entre retry avec backoff et abandon."""
        max_retries = max_retry_override or self.MAX_RETRIES

        if tentative < max_retries or forcer_retry and tentative < self.MAX_RETRIES:
            delai = self.RETRY_BASE_DELAY * (2 ** (tentative - 1))
            delai *= random.uniform(0.75, 1.25)
            log.warning(f"{raison} — retry dans {delai:.1f}s...")
            self._stats["retries_total"] += 1
            time.sleep(delai)
            return self.requeter(url, tentative + 1)
        else:
            log.error(f"{raison} — abandon après {tentative} tentatives")
            self._enregistrer_erreur(raison, url)
            return None

    def _enregistrer_erreur(self, raison: str, url: str = ""):
        self._stats["pages_erreur"] += 1
        self._stats["erreurs"].append({"raison": raison, "url": url[:80] if url else ""})

    def attendre(self):
        delai = random.uniform(self.DELAI_MIN, self.DELAI_MAX)
        log.debug(f"Pause {delai:.1f}s...")
        time.sleep(delai)

    def collecter(self, max_pages: int = 3) -> list[Offre]:
        """Orchestre toute la collecte."""
        log.info(f"{'='*50}")
        log.info(f"🔎 {self.NOM.upper()} — '{self.mot_cle}' à {self.ville}")
        log.info(f"{'='*50}")

        self._stats = {"pages_ok": 0, "pages_erreur": 0, "retries_total": 0, "erreurs": []}
        toutes_offres: list[Offre] = []
        echecs_consecutifs = 0

        for page in range(1, max_pages + 1):
            log.info(f"📄 Page {page}/{max_pages}")

            url = self.construire_url(page)
            soup = self.requeter(url)

            if soup is None:
                echecs_consecutifs += 1
                if echecs_consecutifs >= 2:
                    log.error("Arrêt : 2 échecs consécutifs — site inaccessible")
                    break
                log.warning("Page ignorée — on tente la suivante")
                continue

            echecs_consecutifs = 0
            self._stats["pages_ok"] += 1

            offres_page = self.extraire_offres(soup)
            log.info(f"✅ {len(offres_page)} offres trouvées")

            if not offres_page:
                log.info("Aucune offre — dernière page atteinte")
                break

            toutes_offres.extend(offres_page)

            if not self.a_page_suivante(soup, page):
                log.info("Dernière page atteinte")
                break

            if page < max_pages:
                self.attendre()

        self._afficher_resume(toutes_offres)
        return toutes_offres

    def _afficher_resume(self, offres: list[Offre]):
        stats = self._stats
        total_pages = stats["pages_ok"] + stats["pages_erreur"]

        log.info(f"🏁 {self.NOM} terminé : {len(offres)} offres collectées")
        log.info(f"   Pages OK : {stats['pages_ok']}/{total_pages}")

        if stats["pages_erreur"] > 0:
            log.warning(f"{stats['pages_erreur']} page(s) en erreur, {stats['retries_total']} retries")
            for err in stats["erreurs"]:
                log.warning(f"   ↳ {err['raison']}")
