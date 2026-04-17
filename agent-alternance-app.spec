# -*- mode: python ; coding: utf-8 -*-
"""
agent-alternance-app.spec — Release Application native (PyWebView)
===================================================================

Version avec fenêtre native. Inclut les DLLs pythonnet.

Usage :
    pyinstaller agent-alternance-app.spec --noconfirm
"""

import os

block_cipher = None
RACINE = os.path.dirname(os.path.abspath(SPEC))

# ============================================================
# DATA FILES
# ============================================================

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

# --- Fix PyWebView / pythonnet : embarquer les DLLs .NET ---
try:
    import pythonnet
    pythonnet_dir = os.path.dirname(pythonnet.__file__)
    runtime_dir = os.path.join(pythonnet_dir, 'runtime')
    if os.path.exists(runtime_dir):
        datas.append((runtime_dir, 'pythonnet/runtime'))
    # Embarquer tout le package pythonnet
    datas.append((pythonnet_dir, 'pythonnet'))
except ImportError:
    print("WARN: pythonnet non trouvé — pip install pythonnet")

try:
    import clr_loader
    clr_dir = os.path.dirname(clr_loader.__file__)
    datas.append((clr_dir, 'clr_loader'))
except ImportError:
    print("WARN: clr_loader non trouvé")

try:
    import webview
    webview_dir = os.path.dirname(webview.__file__)
    datas.append((webview_dir, 'webview'))
except ImportError:
    print("WARN: webview non trouvé — pip install pywebview")

# ============================================================
# HIDDEN IMPORTS
# ============================================================

hidden_imports = [
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'fastapi', 'pydantic', 'yaml', 'bs4', 'pdfplumber', 'docx', 'fpdf', 'anthropic',
    'webview', 'webview.platforms.winforms',
    'pythonnet', 'clr', 'clr_loader', 'clr_loader.netfx', 'clr_loader.types',
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

# ============================================================
# BUILD
# ============================================================

a = Analysis(
    ['desktop_app.py'],
    pathex=[RACINE],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL'],
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
    console=False,  # Pas de console visible
    icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='AgentAlternance',
)
