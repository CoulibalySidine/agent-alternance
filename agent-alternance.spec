# -*- mode: python ; coding: utf-8 -*-
"""
agent-alternance.spec — Configuration PyInstaller
===================================================

Génère un .exe autonome avec :
- Le backend Python (FastAPI + tous les modules)
- Le frontend React buildé (frontend/dist/)
- Les fichiers de config (.env.example, profil.yaml)

Usage :
    cd C:\\Users\\SidCo\\Projets\\agent-alternance
    venv\\Scripts\\activate
    pip install pyinstaller pywebview
    npm run build --prefix frontend
    pyinstaller agent-alternance.spec
"""

import os
from pathlib import Path

block_cipher = None

# Dossier racine du projet
RACINE = os.path.dirname(os.path.abspath(SPEC))

# Fichiers de données à inclure dans le .exe
datas = [
    # Frontend buildé
    (os.path.join(RACINE, 'frontend', 'dist'), 'frontend/dist'),

    # Fichiers de config
    (os.path.join(RACINE, '.env.example'), '.'),

    # Profil YAML (template)
    (os.path.join(RACINE, 'qualification', 'profil.yaml'), 'qualification'),
]

# Ajouter .env s'il existe (pour le dev — en production l'utilisateur le crée)
env_file = os.path.join(RACINE, '.env')
if os.path.exists(env_file):
    datas.append((env_file, '.'))

# Modules Python cachés que PyInstaller ne détecte pas automatiquement
hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'pydantic',
    'yaml',
    'bs4',
    'pdfplumber',
    'docx',
    'fpdf',
    'anthropic',
    'webview',

    # Modules du projet
    'config',
    'logger',
    'api',
    'api.main',
    'api.routes',
    'api.routes.sourcing',
    'api.routes.qualification',
    'api.routes.candidature',
    'api.routes.suivi',
    'api.routes.profil',
    'api.schemas',
    'api.tasks',
    'api.deps',
    'sourcing',
    'sourcing.models',
    'sourcing.runner',
    'sourcing.scrapers',
    'sourcing.scrapers.base',
    'sourcing.scrapers.wttj',
    'qualification',
    'qualification.scorer',
    'qualification.runner',
    'candidature',
    'candidature.generateur',
    'candidature.cv_adapter',
    'candidature.fiche_entretien',
    'candidature.reponses_questions',
    'candidature.runner',
    'suivi',
    'suivi.tracker',
    'suivi.dashboard',
    'suivi.runner',
    'profil',
    'profil.extracteur',
    'profil.generateur_profil',
]


a = Analysis(
    ['desktop.py'],
    pathex=[RACINE],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',      # Pas besoin de tkinter
        'matplotlib',   # Pas utilisé
        'numpy',        # Pas utilisé directement
        'scipy',        # Pas utilisé
        'PIL',          # Pas utilisé
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AgentAlternance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Pas de console Windows visible
    icon=None,      # Tu pourras ajouter un .ico ici plus tard
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AgentAlternance',
)
