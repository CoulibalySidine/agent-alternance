# -*- mode: python ; coding: utf-8 -*-
"""
agent-alternance-web.spec — Release Web (navigateur)
=====================================================

Version légère sans PyWebView. Ouvre l'appli dans le navigateur.
Plus fiable, plus petit, zéro problème de DLL.

Usage :
    pyinstaller agent-alternance-web.spec --noconfirm
"""

import os

block_cipher = None
RACINE = os.path.dirname(os.path.abspath(SPEC))

datas = [
    (os.path.join(RACINE, 'frontend', 'dist'), 'frontend/dist'),
    (os.path.join(RACINE, '.env.example'), '.'),
]

env_file = os.path.join(RACINE, '.env')
if os.path.exists(env_file):
    datas.append((env_file, '.'))

profil_file = os.path.join(RACINE, 'qualification', 'profil.yaml')
if os.path.exists(profil_file):
    datas.append((profil_file, 'qualification'))

hidden_imports = [
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'fastapi', 'pydantic', 'yaml', 'bs4', 'pdfplumber', 'docx', 'fpdf', 'anthropic',
    'config', 'logger',
    'api', 'api.main', 'api.routes', 'api.routes.sourcing',
    'api.routes.qualification', 'api.routes.candidature',
    'api.routes.suivi', 'api.routes.profil',
    'api.schemas', 'api.tasks', 'api.deps',
    'sourcing', 'sourcing.models', 'sourcing.runner',
    'sourcing.scrapers', 'sourcing.scrapers.base', 'sourcing.scrapers.wttj',
    'qualification', 'qualification.scorer', 'qualification.runner',
    'candidature', 'candidature.generateur', 'candidature.cv_adapter',
    'candidature.fiche_entretien', 'candidature.reponses_questions', 'candidature.runner',
    'suivi', 'suivi.tracker', 'suivi.dashboard', 'suivi.runner',
    'profil', 'profil.extracteur', 'profil.generateur_profil',
]

a = Analysis(
    ['desktop_web.py'],
    pathex=[RACINE],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL',
              'webview', 'pythonnet', 'clr', 'clr_loader'],  # Exclure PyWebView
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='AgentAlternance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console visible (affiche l'URL)
    icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='AgentAlternance',
)
