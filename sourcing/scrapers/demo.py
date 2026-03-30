"""
demo.py — Scraper de démonstration (données simulées)
=====================================================

POURQUOI CE FICHIER ?
Quand tu développes, tu ne veux pas envoyer 50 requêtes à Indeed
à chaque test. Ce scraper génère des fausses offres réalistes
pour tester tout le pipeline (qualification, candidature, suivi)
sans toucher au réseau.

C'est une bonne pratique pro : toujours avoir un mode "mock"
pour tester sans dépendances externes.
"""

import random
from bs4 import BeautifulSoup
from .base import BaseScraper
from ..models import Offre


# --- Données réalistes pour la génération ---

TITRES = [
    "Alternance Développeur Python",
    "Alternance Développeur Full Stack",
    "Alternance Data Analyst",
    "Alternance Développeur Backend Java",
    "Alternance DevOps / Cloud",
    "Alternance Développeur React / TypeScript",
    "Alternance Ingénieur Data",
    "Alternance Développeur Mobile Flutter",
    "Alternance QA / Test Automation",
    "Alternance Développeur C# / .NET",
    "Alternance Machine Learning Engineer",
    "Alternance Développeur PHP / Symfony",
    "Alternance SRE / Infrastructure",
    "Alternance Développeur API / Microservices",
    "Alternance Cybersécurité",
]

ENTREPRISES = [
    "TechCorp", "DataFlow", "CloudNine", "PixelForge",
    "SmartApps", "NeoSoft", "CyberShield", "CodeFactory",
    "AI Solutions", "WebDynamics", "InnoTech", "ByteCraft",
    "QuantumDev", "AgileWorks", "DigiLab",
]

LIEUX = [
    "Paris", "Paris 8e", "La Défense", "Lyon",
    "Boulogne-Billancourt", "Nanterre", "Toulouse",
    "Bordeaux", "Lille", "Remote / Paris",
]

DESCRIPTIONS = [
    "Rejoins une équipe agile pour développer des APIs REST en Python/FastAPI. "
    "Tu participeras à la conception et au déploiement de microservices.",

    "Nous recherchons un(e) alternant(e) passionné(e) par la data. "
    "Tu travailleras sur des pipelines ETL et des dashboards avec Python et SQL.",

    "Intègre notre squad produit pour développer de nouvelles features "
    "sur notre application React/Node.js utilisée par 50k+ utilisateurs.",

    "Tu contribueras à notre infrastructure cloud (AWS/GCP) et à la mise en place "
    "de pipelines CI/CD. Ambiance startup, stack moderne.",

    "Participe au développement de notre plateforme SaaS B2B. "
    "Stack : TypeScript, React, PostgreSQL, Docker. Télétravail 2j/semaine.",

    "Rejoins l'équipe IA pour entraîner et déployer des modèles NLP. "
    "Python, PyTorch, transformers. Encadrement par un ML Engineer senior.",
]

SALAIRES = [
    "1 000 € - 1 200 € par mois", "1 100 € - 1 400 € par mois",
    "900 € - 1 100 € par mois", None, None,  # Pas toujours précisé
]


class DemoScraper(BaseScraper):
    """
    Scraper de test qui génère des offres fictives réalistes.

    Même interface que les vrais scrapers (hérite de BaseScraper),
    donc le reste du pipeline ne voit aucune différence.

    C'est le Liskov Substitution Principle (le 'L' de SOLID) :
    on peut remplacer BaseScraper par DemoScraper partout.
    """

    NOM = "demo"

    def __init__(self, mot_cle: str = "alternance développeur", ville: str = "Paris",
                 nb_offres: int = 12):
        super().__init__(mot_cle, ville)
        self.nb_offres = nb_offres
        self.offres_par_page = 5

    def construire_url(self, page: int = 1) -> str:
        """Pas de vraie URL, mais on respecte l'interface."""
        return f"https://demo.local/jobs?q={self.mot_cle}&page={page}"

    def extraire_offres(self, soup: BeautifulSoup) -> list[Offre]:
        """
        Génère des offres aléatoires au lieu de parser du HTML.
        Le paramètre `soup` est ignoré (on n'a pas de vrai HTML).
        """
        nb = min(self.offres_par_page, self.nb_offres - len(self._offres_generees))
        offres = []

        for _ in range(nb):
            offre = Offre(
                titre=random.choice(TITRES),
                entreprise=random.choice(ENTREPRISES),
                url=f"https://demo.local/offre/{random.randint(1000, 9999)}",
                source=self.NOM,
                lieu=random.choice(LIEUX),
                description=random.choice(DESCRIPTIONS),
                salaire=random.choice(SALAIRES),
            )
            offres.append(offre)
            self._offres_generees.append(offre)

        return offres

    def a_page_suivante(self, soup: BeautifulSoup, page_actuelle: int) -> bool:
        """Continue tant qu'on n'a pas généré assez d'offres."""
        return len(self._offres_generees) < self.nb_offres

    def requeter(self, url: str):
        """Override : pas de vraie requête HTTP, retourne un soup vide."""
        print(f"  🎭 [DEMO] Génération de données simulées...")
        return BeautifulSoup("<html></html>", "html.parser")

    def attendre(self):
        """Override : pas besoin d'attendre en mode démo."""
        pass

    def collecter(self, max_pages: int = 3) -> list[Offre]:
        """Override pour initialiser le compteur avant la collecte."""
        self._offres_generees = []
        return super().collecter(max_pages)
