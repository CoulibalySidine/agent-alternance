"""
desktop_web.py — Lanceur Web (navigateur par défaut)
=====================================================

Version légère : lance FastAPI et ouvre le navigateur.
Pas de PyWebView, pas de pythonnet, zéro problème de DLL.

Usage :
    python desktop_web.py

Pour créer le .exe :
    pyinstaller agent-alternance-web.spec
"""

import sys
import os
import time
import threading
import socket
import webbrowser

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
    port = trouver_port_libre()
    url = f"http://{HOST}:{port}"

    # Lancer FastAPI dans un thread daemon
    thread = threading.Thread(target=lancer_serveur, args=(port,), daemon=True)
    thread.start()

    if not attendre_serveur(HOST, port):
        print("Erreur : le serveur n'a pas démarré.")
        sys.exit(1)

    print()
    print("  ================================")
    print("   Agent Alternance")
    print(f"   {url}")
    print("  ================================")
    print()
    print("  L'appli est ouverte dans ton navigateur.")
    print("  Pour arreter : ferme cette fenetre ou Ctrl+C")
    print()

    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Arret de l'application.")


if __name__ == "__main__":
    main()
