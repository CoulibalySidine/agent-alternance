"""
logger.py — Logging centralisé du projet
==========================================

CONCEPT CLÉ : le module logging de Python.

POURQUOI PAS print() ?
1. print() va dans stdout et disparaît quand le terminal se ferme
2. Pas de niveaux : impossible de filtrer les erreurs des infos
3. Pas de timestamp : quand est-ce que ça s'est passé ?
4. Pas de source : quel module a généré ce message ?

COMMENT ÇA MARCHE :
- On configure UN logger racine pour tout le projet
- Chaque module fait : from logger import get_logger puis log = get_logger("module")
- Les messages vont dans le terminal ET dans un fichier logs/agent.log
- 4 niveaux : DEBUG, INFO, WARNING, ERROR

QUAND GARDER print() ?
- Les menus CLI interactifs (suivi/runner.py)
- Les barres de progression
- L'affichage formaté pour l'utilisateur
→ Tout ce qui EST l'interface utilisateur reste en print()

QUAND UTILISER le logger ?
- Requêtes réseau (GET, POST, retry, timeout)
- Succès/échecs d'opérations (scoring, génération, sauvegarde)
- Erreurs et warnings
- Stats de collecte
→ Tout ce qui est un ÉVÉNEMENT du système
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


# =================================================================
# CONFIGURATION
# =================================================================

# Dossier des logs (à la racine du projet)
RACINE_PROJET = Path(__file__).parent
LOG_DIR = RACINE_PROJET / "logs"
LOG_FILE = LOG_DIR / "agent.log"

# Niveau par défaut (DEBUG = tout afficher, INFO = sans les détails réseau)
DEFAULT_LEVEL = logging.INFO

# Taille max du fichier log avant rotation (5 Mo)
MAX_LOG_SIZE = 5 * 1024 * 1024
# Nombre de fichiers de backup à garder
BACKUP_COUNT = 3


# =================================================================
# FORMATEURS
# =================================================================

class EmojiFormatter(logging.Formatter):
    """
    Formateur pour le terminal : emojis + couleurs selon le niveau.

    DEBUG   → 🔍 (gris, détails réseau)
    INFO    → ✅ (normal, opérations réussies)
    WARNING → ⚠️  (jaune, à surveiller)
    ERROR   → ❌ (rouge, problème)
    """

    FORMATS = {
        logging.DEBUG:   "  🔍 %(message)s",
        logging.INFO:    "  %(message)s",
        logging.WARNING: "  ⚠️  %(message)s",
        logging.ERROR:   "  ❌ %(message)s",
    }

    def format(self, record):
        fmt = self.FORMATS.get(record.levelno, "  %(message)s")
        formatter = logging.Formatter(fmt)
        return formatter.format(record)


# Format du fichier log (plus détaillé, avec timestamp et source)
FILE_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s"
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# =================================================================
# SETUP
# =================================================================

_configured = False


def _setup_logging():
    """
    Configure le système de logging une seule fois.

    Deux handlers :
    1. Console (stdout) : emojis, pas de timestamp (le terminal est live)
    2. Fichier (logs/agent.log) : timestamp + source + niveau (pour relire après)
    """
    global _configured
    if _configured:
        return
    _configured = True

    # Créer le dossier logs
    LOG_DIR.mkdir(exist_ok=True)

    # Logger racine du projet
    root = logging.getLogger("agent")
    root.setLevel(logging.DEBUG)  # Capturer tout, filtrer par handler

    # Ne pas propager au logger racine de Python (évite les doublons)
    root.propagate = False

    # Vider les handlers existants (en cas de rechargement)
    root.handlers.clear()

    # --- Handler console ---
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(DEFAULT_LEVEL)
    console.setFormatter(EmojiFormatter())
    root.addHandler(console)

    # --- Handler fichier (avec rotation) ---
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Tout dans le fichier
        file_handler.setFormatter(
            logging.Formatter(FILE_FORMAT, datefmt=FILE_DATE_FORMAT)
        )
        root.addHandler(file_handler)
    except Exception as e:
        # Si on ne peut pas écrire le fichier, on continue quand même
        console.setLevel(logging.DEBUG)
        root.warning(f"Impossible de créer le fichier log : {e}")


# =================================================================
# API PUBLIQUE
# =================================================================

def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger pour un module.

    Usage dans chaque fichier du projet :
        from logger import get_logger
        log = get_logger("sourcing.wttj")

        log.info("20 offres collectées")
        log.warning("Rate limit atteint")
        log.error("Timeout après 3 retries")
        log.debug("POST algolia.net page=2")

    Args:
        name: nom du module (ex: "sourcing.wttj", "candidature", "suivi")

    Returns:
        Un logger configuré avec le bon préfixe
    """
    _setup_logging()
    return logging.getLogger(f"agent.{name}")


def set_level(level: str):
    """
    Change le niveau de log du terminal.

    Args:
        level: "DEBUG", "INFO", "WARNING", "ERROR"

    Usage :
        from logger import set_level
        set_level("DEBUG")  # Voir les détails réseau
    """
    _setup_logging()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    lvl = level_map.get(level.upper(), logging.INFO)
    root = logging.getLogger("agent")
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and not hasattr(handler, 'baseFilename'):
            handler.setLevel(lvl)


def log_separator(title: str = "", char: str = "=", width: int = 50):
    """
    Affiche un séparateur dans les logs.
    Utile pour marquer le début d'une opération.
    """
    log = get_logger("system")
    if title:
        log.info(f"{char*width}")
        log.info(f"  {title}")
        log.info(f"{char*width}")
    else:
        log.info(f"{char*width}")
