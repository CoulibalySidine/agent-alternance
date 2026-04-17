"""
desktop_app.py — Lanceur Application native (PyWebView)
=========================================================

Version native : ouvre une fenêtre dédiée (pas le navigateur).
Nécessite PyWebView + pythonnet.

Usage :
    python desktop_app.py

Pour créer le .exe :
    pyinstaller agent-alternance-app.spec
"""

import sys
import os
import time
import threading
import socket

# Fixer le répertoire de travail
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config  # noqa: E402

HOST = "127.0.0.1"


def port_disponible(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def trouver_port_libre(debut: int = 8000, fin: int = 8100) -> int:
    for port in range(debut, fin):
        if port_disponible(HOST, port):
            return port
    raise RuntimeError(f"Aucun port libre trouvé entre {debut} et {fin}")


def attendre_serveur(host: str, port: int, timeout: int = 15) -> bool:
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
    import uvicorn
    from api.main import app
    uvicorn.run(app, host=HOST, port=port, log_level="warning")


def main():
    import webview

    port = trouver_port_libre()

    thread = threading.Thread(target=lancer_serveur, args=(port,), daemon=True)
    thread.start()

    if not attendre_serveur(HOST, port):
        print("Erreur : le serveur n'a pas démarré.")
        sys.exit(1)

    fenetre = webview.create_window(
        title="Agent Alternance",
        url=f"http://{HOST}:{port}",
        width=1280,
        height=800,
        min_size=(900, 600),
        confirm_close=False,
    )

    webview.start(debug=not getattr(sys, "frozen", False))


if __name__ == "__main__":
    main()
