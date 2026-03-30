"""
config.py — Configuration centralisée du projet
=================================================

CONCEPT CLÉ : Single Source of Truth.

Au lieu d'avoir des clés API, des chemins et des seuils
éparpillés dans 8 fichiers différents, tout est ici.

COMMENT ÇA MARCHE :
1. On cherche un fichier .env à la racine du projet
2. On lit chaque ligne CLÉ=VALEUR
3. On expose tout via des constantes Python

Les autres modules font :
    from config import API_KEY, MODEL, SCORE_MINIMUM

Si une valeur n'est pas dans .env, on utilise la valeur par défaut.
Si .env n'existe pas, tout fonctionne quand même avec les défauts
(sauf la clé API qui est obligatoire).

PAS DE DÉPENDANCE EXTERNE : on ne dépend pas de python-dotenv.
Le parsing du .env est fait à la main — c'est 15 lignes de code.
"""

import os
from pathlib import Path


# =================================================================
# CHARGEMENT DU .env (sans dépendance externe)
# =================================================================

# Le fichier .env est à la racine du projet (à côté de sourcing/, suivi/, etc.)
RACINE_PROJET = Path(__file__).parent
ENV_PATH = RACINE_PROJET / ".env"


def _charger_env(chemin: Path = ENV_PATH) -> dict:
    """
    Parse un fichier .env et retourne un dict {clé: valeur}.

    Format supporté :
        CLÉ=valeur
        CLÉ="valeur avec espaces"
        # commentaire
        (lignes vides ignorées)

    Les valeurs sont aussi injectées dans os.environ pour que
    les librairies tierces (comme anthropic SDK) les trouvent.
    """
    valeurs = {}

    if not chemin.exists():
        return valeurs

    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()

        # Ignorer les commentaires et lignes vides
        if not ligne or ligne.startswith("#"):
            continue

        # Séparer clé et valeur (seulement au premier =)
        if "=" not in ligne:
            continue

        cle, valeur = ligne.split("=", 1)
        cle = cle.strip()
        valeur = valeur.strip()

        # Retirer les guillemets si présents
        if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in ('"', "'"):
            valeur = valeur[1:-1]

        valeurs[cle] = valeur

        # Injecter dans os.environ (pour que les SDK les trouvent)
        # Ne PAS écraser une variable déjà définie dans le système
        if cle not in os.environ:
            os.environ[cle] = valeur

    return valeurs


# Charger le .env au démarrage
_env = _charger_env()


def env(cle: str, defaut: str = "") -> str:
    """Récupère une valeur : .env → variable système → défaut."""
    return _env.get(cle, os.environ.get(cle, defaut))


def env_int(cle: str, defaut: int = 0) -> int:
    """Récupère une valeur entière."""
    try:
        return int(env(cle, str(defaut)))
    except ValueError:
        return defaut


def env_float(cle: str, defaut: float = 0.0) -> float:
    """Récupère une valeur flottante."""
    try:
        return float(env(cle, str(defaut)))
    except ValueError:
        return defaut


# =================================================================
# CONSTANTES DU PROJET (utilisées par tous les modules)
# =================================================================

# --- API Anthropic ---
API_KEY = env("ANTHROPIC_API_KEY")
MODEL = env("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# --- Algolia (WTTJ) ---
ALGOLIA_APP_ID = env("ALGOLIA_APP_ID", "CSEKHVMS53")
ALGOLIA_API_KEY = env("ALGOLIA_API_KEY", "4bd8f6215d0cc52b26430765769e65a0")
ALGOLIA_INDEX = env("ALGOLIA_INDEX", "wttj_jobs_production_fr")

# --- Scraping ---
SCRAPING_DELAI_MIN = env_float("SCRAPING_DELAI_MIN", 1.0)
SCRAPING_DELAI_MAX = env_float("SCRAPING_DELAI_MAX", 3.0)
SCRAPING_MAX_RETRIES = env_int("SCRAPING_MAX_RETRIES", 3)
SCRAPING_MAX_PAGES = env_int("SCRAPING_MAX_PAGES", 3)

# --- Qualification / Candidature ---
SCORE_MINIMUM = env_int("SCORE_MINIMUM", 60)
MAX_DOSSIERS = env_int("MAX_DOSSIERS", 3)

# --- Chemins (relatifs à la racine du projet) ---
FICHIER_OFFRES = RACINE_PROJET / "sourcing" / "offres.json"
FICHIER_SUIVI = RACINE_PROJET / "suivi" / "suivi.json"
FICHIER_PROFIL = RACINE_PROJET / "qualification" / "profil.yaml"
DOSSIER_LETTRES = RACINE_PROJET / "candidature" / "lettres"
DOSSIER_DASHBOARD = RACINE_PROJET / "suivi"


# =================================================================
# VALIDATION (au chargement)
# =================================================================

def verifier_config():
    """
    Vérifie que la configuration est valide.
    Appelé manuellement par les runners qui ont besoin de l'API.
    """
    erreurs = []

    if not API_KEY:
        erreurs.append(
            "ANTHROPIC_API_KEY non définie.\n"
            "   → Crée un fichier .env à la racine avec : ANTHROPIC_API_KEY=sk-ant-...\n"
            "   → Ou définis la variable d'environnement système."
        )
    elif not API_KEY.startswith("sk-ant-"):
        erreurs.append(
            f"ANTHROPIC_API_KEY semble invalide (ne commence pas par 'sk-ant-').\n"
            f"   → Valeur actuelle : {API_KEY[:12]}..."
        )

    if erreurs:
        print(f"\n{'='*60}")
        print(f"⚠️  PROBLÈMES DE CONFIGURATION")
        print(f"{'='*60}")
        for err in erreurs:
            print(f"\n  ❌ {err}")
        print(f"\n{'='*60}\n")
        return False

    return True


# =================================================================
# AFFICHAGE (debug)
# =================================================================

def afficher_config():
    """Affiche la configuration active (masque la clé API)."""
    api_masquee = f"{API_KEY[:12]}...{API_KEY[-4:]}" if len(API_KEY) > 16 else "(non définie)"

    print(f"\n⚙️  Configuration active :")
    print(f"   API Key      : {api_masquee}")
    print(f"   Modèle       : {MODEL}")
    print(f"   Algolia      : {ALGOLIA_APP_ID} / {ALGOLIA_INDEX}")
    print(f"   Scraping     : {SCRAPING_MAX_PAGES} pages, délai {SCRAPING_DELAI_MIN}-{SCRAPING_DELAI_MAX}s, {SCRAPING_MAX_RETRIES} retries")
    print(f"   Score min    : {SCORE_MINIMUM}")
    print(f"   Max dossiers : {MAX_DOSSIERS}")
    print(f"   .env chargé  : {'✅ ' + str(ENV_PATH) if ENV_PATH.exists() else '❌ non trouvé'}")
    print()
