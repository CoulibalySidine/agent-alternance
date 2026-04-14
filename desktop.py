"""
desktop.py — Lanceur Desktop (PyWebView + FastAPI)
====================================================

Ce script :
1. Lance le serveur FastAPI dans un thread séparé
2. Attend que le serveur soit prêt
3. Ouvre une fenêtre native PyWebView pointant vers le frontend

Usage :
    python desktop.py

Pour créer le .exe :
    pyinstaller agent-alternance.spec
"""

import sys
import os
import time
import threading
import socket

# Fixer le répertoire de travail au dossier du script
# (important pour PyInstaller qui change le cwd)
if getattr(sys, "frozen", False):
    # Mode PyInstaller : le .exe est dans un dossier temporaire
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

# Ajouter le dossier au path Python
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Charger la config (.env) avant tout
import config  # noqa: E402

PORT = 8000
HOST = "127.0.0.1"


def port_disponible(host: str, port: int) -> bool:
    """Vérifie si le port est libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def trouver_port_libre(debut: int = 8000, fin: int = 8100) -> int:
    """Trouve un port libre dans la plage donnée."""
    for port in range(debut, fin):
        if port_disponible(HOST, port):
            return port
    raise RuntimeError(f"Aucun port libre trouvé entre {debut} et {fin}")


def attendre_serveur(host: str, port: int, timeout: int = 15) -> bool:
    """Attend que le serveur soit prêt (max timeout secondes)."""
    debut = time.time()
    while time.time() - debut < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def lancer_serveur(port: int):
    """Lance le serveur FastAPI avec Uvicorn."""
    import uvicorn
    from api.main import app

    uvicorn.run(
        app,
        host=HOST,
        port=port,
        log_level="warning",
        # Pas de reload en mode desktop
    )


def main():
    import webview

    # Trouver un port libre
    port = trouver_port_libre()

    # Lancer FastAPI dans un thread daemon
    thread_serveur = threading.Thread(
        target=lancer_serveur,
        args=(port,),
        daemon=True,  # Se ferme automatiquement quand la fenêtre se ferme
    )
    thread_serveur.start()

    # Attendre que le serveur soit prêt
    if not attendre_serveur(HOST, port):
        print("Erreur : le serveur n'a pas démarré dans les temps.")
        sys.exit(1)

    # Ouvrir la fenêtre PyWebView
    fenetre = webview.create_window(
        title="Agent Alternance",
        url=f"http://{HOST}:{port}",
        width=1280,
        height=800,
        min_size=(900, 600),
        confirm_close=False,
    )

    # Bloquer ici jusqu'à fermeture de la fenêtre
    webview.start(
        debug=not getattr(sys, "frozen", False),  # Debug en dev, pas en .exe
    )


if __name__ == "__main__":
    main()
