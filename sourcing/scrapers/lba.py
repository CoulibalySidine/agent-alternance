"""
lba.py — Scraper La bonne alternance via API officielle
=========================================================

Source la plus riche pour l'alternance en France.
Agrège France Travail + 1jeune1solution + partenaires.
~225 000 offres en temps réel.

ARCHITECTURE :
1. Géocode la ville via api-adresse.data.gouv.fr (gratuit, sans clé)
2. Convertit les mots-clés en codes ROME (référentiel métiers)
3. Appelle l'API La bonne alternance
4. Convertit les résultats en objets Offre

API docs : https://api.apprentissage.beta.gouv.fr/fr/explorer/recherche-offre
"""

import json
import time
from typing import Optional
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import Offre
from logger import get_logger

try:
    import requests
except ImportError:
    raise ImportError("pip install requests")

log = get_logger("sourcing.lba")


# =========================================================================
# MAPPING MOTS-CLÉS → CODES ROME
# =========================================================================
# Les codes ROME sont le référentiel officiel de France Travail.
# On mappe les mots-clés courants vers les codes pertinents.
# Liste complète : https://www.france-travail.fr/employeur/vos-recrutements/le-rome-et-les-fiches-metiers.html

ROME_MAPPING = {
    # Développement
    "développeur": ["M1805"],
    "developpeur": ["M1805"],
    "dev": ["M1805"],
    "fullstack": ["M1805"],
    "full-stack": ["M1805"],
    "full stack": ["M1805"],
    "backend": ["M1805"],
    "frontend": ["M1805"],
    "front-end": ["M1805"],
    "back-end": ["M1805"],
    "python": ["M1805"],
    "java": ["M1805"],
    "javascript": ["M1805"],
    "react": ["M1805"],
    "php": ["M1805"],
    "c#": ["M1805"],
    ".net": ["M1805"],
    "mobile": ["M1805"],
    "flutter": ["M1805"],
    "swift": ["M1805"],
    "android": ["M1805"],
    "ios": ["M1805"],
    "web": ["M1805"],
    "logiciel": ["M1805"],
    "software": ["M1805"],
    "programmeur": ["M1805"],
    "codeur": ["M1805"],

    # Data
    "data": ["M1805", "M1403"],
    "data analyst": ["M1403"],
    "data engineer": ["M1805"],
    "data scientist": ["M1805", "M1403"],
    "machine learning": ["M1805"],
    "ia": ["M1805"],
    "intelligence artificielle": ["M1805"],
    "big data": ["M1805", "M1403"],
    "bi": ["M1403"],
    "business intelligence": ["M1403"],

    # Systèmes / Infra / DevOps
    "devops": ["M1801"],
    "sysadmin": ["M1801"],
    "système": ["M1801"],
    "systeme": ["M1801"],
    "réseau": ["M1801"],
    "reseau": ["M1801"],
    "cloud": ["M1801"],
    "infrastructure": ["M1801"],
    "sre": ["M1801"],
    "linux": ["M1801"],
    "aws": ["M1801"],

    # Cybersécurité
    "cybersécurité": ["M1802"],
    "cybersecurite": ["M1802"],
    "sécurité informatique": ["M1802"],
    "securite informatique": ["M1802"],
    "sécurité": ["M1802"],
    "pentest": ["M1802"],
    "soc": ["M1802"],

    # Chef de projet / Product
    "chef de projet": ["M1806"],
    "project manager": ["M1806"],
    "product owner": ["M1806"],
    "product manager": ["M1806"],
    "scrum master": ["M1806"],
    "agile": ["M1806"],

    # Support / QA
    "support": ["M1801"],
    "helpdesk": ["M1801"],
    "qa": ["M1805"],
    "test": ["M1805"],
    "qualité": ["M1805"],

    # Design
    "ux": ["E1205"],
    "ui": ["E1205"],
    "design": ["E1205"],
    "ux/ui": ["E1205"],
    "webdesign": ["E1205"],

    # Marketing digital
    "marketing digital": ["E1401"],
    "seo": ["E1401"],
    "community manager": ["E1401"],
    "growth": ["E1401"],

    # Termes génériques alternance
    "alternance": ["M1805"],
    "informatique": ["M1805", "M1801"],
    "numérique": ["M1805"],
    "digital": ["M1805"],
    "it": ["M1805", "M1801"],
    "tech": ["M1805"],
}

# Codes ROME par défaut si aucun mot-clé ne matche
DEFAULT_ROMES = ["M1805", "M1801", "M1802", "M1806"]


# =========================================================================
# GÉOCODAGE
# =========================================================================

def geocoder_ville(ville: str) -> Optional[dict]:
    """
    Convertit un nom de ville en coordonnées GPS.
    Utilise l'API Adresse du gouvernement (gratuite, sans clé).

    Returns:
        {"lat": 48.8566, "lon": 2.3522, "label": "Paris"} ou None
    """
    try:
        resp = requests.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": ville, "type": "municipality", "limit": 1},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("features"):
            feature = data["features"][0]
            coords = feature["geometry"]["coordinates"]
            label = feature["properties"].get("label", ville)
            return {
                "lat": coords[1],  # GeoJSON = [lon, lat]
                "lon": coords[0],
                "label": label,
            }
    except Exception as e:
        log.warning(f"Géocodage échoué pour '{ville}' : {e}")

    return None


def extraire_codes_rome(mot_cle: str) -> list[str]:
    """
    Extrait les codes ROME pertinents depuis les mots-clés de recherche.

    Stratégie : cherche chaque mot et combinaison dans le mapping.
    Déduplique et limite à 20 codes (max API).
    """
    mot_cle_lower = mot_cle.lower().strip()
    codes = set()

    # Essayer le mot-clé complet d'abord
    if mot_cle_lower in ROME_MAPPING:
        codes.update(ROME_MAPPING[mot_cle_lower])

    # Puis chaque mot individuellement
    for mot in mot_cle_lower.split():
        mot = mot.strip(",.;:!?()[]")
        if mot in ROME_MAPPING:
            codes.update(ROME_MAPPING[mot])

    # Essayer les combinaisons de 2 mots
    mots = mot_cle_lower.split()
    for i in range(len(mots) - 1):
        combo = f"{mots[i]} {mots[i+1]}"
        if combo in ROME_MAPPING:
            codes.update(ROME_MAPPING[combo])

    if not codes:
        log.info(f"Aucun code ROME trouvé pour '{mot_cle}', utilisation des codes par défaut")
        codes = set(DEFAULT_ROMES)

    result = list(codes)[:20]
    log.info(f"Codes ROME pour '{mot_cle}' : {', '.join(result)}")
    return result


# =========================================================================
# SCRAPER
# =========================================================================

class LbaScraper(BaseScraper):
    """
    Scraper La bonne alternance via API REST officielle.

    Contrairement aux autres scrapers qui parsent du HTML,
    celui-ci appelle une vraie API JSON. On override la
    méthode `collecter()` car la logique de pagination
    est différente (pas de pages HTML à parcourir).
    """

    NOM = "lba"

    API_BASE = "https://api.apprentissage.beta.gouv.fr/api"
    CALLER = "agent-alternance"  # Identifiant requis par l'API
    RADIUS = 30  # Rayon de recherche en km

    def __init__(
        self,
        mot_cle: str = "alternance développeur",
        ville: str = "Paris",
        radius: int = 30,
    ):
        super().__init__(mot_cle, ville)
        self.radius = radius
        self.geo = None
        self.rome_codes = []
        
    

    def construire_url(self, page: int = 1) -> str:
        """Non utilisé directement (on override collecter)."""
        return f"{self.API_BASE}/V1/jobs"

    def extraire_offres(self, soup: BeautifulSoup) -> list[Offre]:
        """Non utilisé directement (on override collecter)."""
        return []
    
    def _get_token(self):
        """Récupère le token LBA depuis la config."""
        from config import env
        token = env("LBA_API_TOKEN", "")
        if not token:
            log.warning("LBA_API_TOKEN non configuré dans .env")
        return token


    def a_page_suivante(self, soup: BeautifulSoup, page_actuelle: int) -> bool:
        """Non utilisé directement."""
        return False

    def collecter(self, max_pages: int = 3) -> list[Offre]:
        """
        Collecte les offres via l'API La bonne alternance.

        Override complet de BaseScraper.collecter() car :
        - Pas de pagination HTML (l'API retourne tout d'un coup)
        - Requête JSON, pas HTML
        - Géocodage préalable nécessaire
        """
        log.info(f"{'='*50}")
        log.info(f"🔎 LBA — '{self.mot_cle}' à {self.ville}")
        log.info(f"{'='*50}")

        # 1. Géocoder la ville
        self.geo = geocoder_ville(self.ville)
        if not self.geo:
            log.error(f"Impossible de géocoder '{self.ville}' — abandon")
            return []

        log.info(f"📍 Géocodage : {self.geo['label']} ({self.geo['lat']}, {self.geo['lon']})")

        # 2. Extraire les codes ROME
        self.rome_codes = extraire_codes_rome(self.mot_cle)

        # 3. Appeler l'API
        offres = self._rechercher_offres()

        log.info(f"{'='*50}")
        log.info(f"🏁 LBA terminé : {len(offres)} offres collectées")
        log.info(f"{'='*50}")

        if offres:
            log.info("📌 Aperçu :")
            for o in offres[:5]:
                log.info(f"   {o.résumé()}")
            if len(offres) > 5:
                log.info(f"   ... et {len(offres) - 5} autres")

        return offres

    def _rechercher_offres(self) -> list[Offre]:
        """Appelle l'API et convertit les résultats en Offre."""
        toutes_offres = []

        params = {
            "romes": ",".join(self.rome_codes),
            "latitude": self.geo["lat"],
            "longitude": self.geo["lon"],
            "radius": self.radius,
            "caller": self.CALLER,
        }

        try:
            log.info(f"📡 Appel API LBA (ROME: {params['romes']}, rayon: {self.radius}km)")

            resp = self.session.get(
                f"{self.API_BASE}/job/v1/search",
                params=params,
                headers={"Authorization": f"Bearer {self._get_token()}"},
                timeout=30,
            )

            if resp.status_code == 429:
                log.warning("Rate limit atteint — attente 5s")
                time.sleep(5)
                resp = self.session.get(
                    f"{self.API_BASE}/job/v1/search",
                    params=params,
                    headers={"Authorization": f"Bearer {self._get_token()}"},
                    timeout=30,
                )

            if resp.status_code != 200:
                log.error(f"API LBA erreur {resp.status_code} : {resp.text[:200]}")
                return []

            data = resp.json()

        except requests.exceptions.Timeout:
            log.error("Timeout API LBA (30s)")
            return []
        except requests.exceptions.RequestException as e:
            log.error(f"Erreur réseau API LBA : {e}")
            return []
        except json.JSONDecodeError:
            log.error("Réponse API LBA invalide (pas du JSON)")
            return []

        # Parser les offres (jobs)
        jobs = data.get("jobs", [])
        for item in jobs:
            offre = self._parser_job(item)
            if offre:
                toutes_offres.append(offre)
        log.info(f"   Offres d'emploi : {len(jobs)} trouvées, {sum(1 for j in jobs if self._parser_job(j))} parsées")

        # Parser les recruteurs (candidatures spontanées)
        recruiters = data.get("recruiters", [])
        for item in recruiters:
            offre = self._parser_recruiter(item)
            if offre:
                toutes_offres.append(offre)
        log.info(f"   Entreprises à potentiel : {len(recruiters)} opportunités")

        return toutes_offres

    def _parser_job(self, item: dict) -> Optional[Offre]:
        """Parse une offre d'emploi (structure v1 : identifier/workplace/offer/contract/apply)."""
        try:
            # Titre
            offer = item.get("offer", {})
            titre = offer.get("title", "Offre sans titre").strip()

            # Entreprise
            workplace = item.get("workplace", {})
            entreprise = workplace.get("name") or workplace.get("brand") or workplace.get("legal_name") or "Entreprise non précisée"

            # Lieu
            location = workplace.get("location", {})
            address = location.get("address", "Non précisé")
            # Extraire la ville depuis l'adresse (dernier mot après le code postal)
            lieu = address

            # Description
            description = offer.get("description", "")

            # URL
            apply_info = item.get("apply", {})
            url = apply_info.get("url", "")

            # Contrat
            contract = item.get("contract", {})
            types_contrat = contract.get("type", [])
            type_contrat = ", ".join(types_contrat) if types_contrat else "Alternance"
            duree = contract.get("duration")
            date_debut = contract.get("start", "")

            # Enrichir la description
            extras = []
            if duree:
                extras.append(f"Durée : {duree} mois")
            if date_debut:
                extras.append(f"Début : {date_debut[:10]}")
            remote = contract.get("remote")
            if remote:
                extras.append(f"Mode : {remote}")

            target_diploma = offer.get("target_diploma", {})
            if isinstance(target_diploma, dict) and target_diploma.get("label"):
                extras.append(f"Diplôme visé : {target_diploma['label']}")

            if extras:
                description = description + "\n\n" + " | ".join(extras)

            # Source label
            identifier = item.get("identifier", {})
            partner = identifier.get("partner_label", "lba")

            return Offre(
                titre=titre,
                entreprise=entreprise,
                url=url,
                source="lba",
                lieu=lieu,
                description=description[:2000] if description else "",
                type_contrat=type_contrat,
            )
        except Exception as e:
            log.warning(f"Erreur parsing job : {e}")
            return None

    def _parser_recruiter(self, item: dict) -> Optional[Offre]:
        """Parse une entreprise à potentiel (candidature spontanée)."""
        try:
            workplace = item.get("workplace", {})
            entreprise = workplace.get("name") or workplace.get("brand") or workplace.get("legal_name") or "Entreprise non précisée"

            location = workplace.get("location", {})
            lieu = location.get("address", "Non précisé")

            # Description depuis les métadonnées
            domain = workplace.get("domain", {})
            description_parts = []

            naf = domain.get("naf", {})
            if isinstance(naf, dict) and naf.get("label"):
                description_parts.append(f"Secteur : {naf['label']}")

            opco = domain.get("opco")
            if opco and opco != "inconnu":
                description_parts.append(f"OPCO : {opco}")

            size = workplace.get("size")
            if size and size != "None":
                description_parts.append(f"Taille : {size}")

            description_parts.append(
                "Entreprise identifiée comme ayant un fort potentiel "
                "d'embauche en alternance. Candidature spontanée recommandée."
            )

            apply_info = item.get("apply", {})
            url = apply_info.get("url", "")

            naf_label = naf.get("label", "") if isinstance(naf, dict) else ""
            titre = f"Candidature spontanée — {naf_label}" if naf_label else "Candidature spontanée"

            return Offre(
                titre=titre,
                entreprise=entreprise,
                url=url,
                source="lba",
                lieu=lieu,
                description="\n".join(description_parts),
                type_contrat="Alternance (spontanée)",
            )
        except Exception as e:
            log.warning(f"Erreur parsing recruiter : {e}")
            return None
