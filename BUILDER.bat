@echo off
title Agent Alternance - Build Desktop
echo.
echo  ===================================
echo   Agent Alternance - Build .exe
echo  ===================================
echo.

cd /d "%~dp0"

:: Verifier le venv
if not exist venv\Scripts\activate (
    echo  [ERREUR] Le venv n'existe pas. Lance d'abord INSTALLER.bat
    pause
    exit /b 1
)

call venv\Scripts\activate

:: -----------------------------------------------
:: Etape 1 : Installer les dependances de build
:: -----------------------------------------------
echo  [1/4] Installation de PyWebView et PyInstaller...
pip install pywebview pyinstaller --quiet
if errorlevel 1 (
    echo  [ERREUR] Impossible d'installer les dependances de build
    pause
    exit /b 1
)
echo        OK

:: -----------------------------------------------
:: Etape 2 : Builder le frontend React
:: -----------------------------------------------
echo  [2/4] Build du frontend React...
cd frontend
call npm run build
if errorlevel 1 (
    echo  [ERREUR] Le build du frontend a echoue
    echo  Verifie que Node.js est installe et que npm install a ete fait
    cd ..
    pause
    exit /b 1
)
cd ..

if not exist frontend\dist\index.html (
    echo  [ERREUR] Le build n'a pas genere frontend\dist\index.html
    pause
    exit /b 1
)
echo        OK

:: -----------------------------------------------
:: Etape 3 : Remplacer api/main.py par la version desktop
:: -----------------------------------------------
echo  [3/4] Preparation du backend pour le mode desktop...

:: Sauvegarder l'original si pas deja fait
if not exist api\main_dev.py.bak (
    copy api\main.py api\main_dev.py.bak >nul
)

:: Le main.py doit deja avoir le patch static files
:: Si tu n'as pas encore applique le patch, decommenter la ligne suivante :
:: copy api_main_patched.py api\main.py >nul

echo        OK

:: -----------------------------------------------
:: Etape 4 : Creer le .exe avec PyInstaller
:: -----------------------------------------------
echo  [4/4] Creation du .exe (cela peut prendre 2-3 minutes)...
pyinstaller agent-alternance.spec --noconfirm
if errorlevel 1 (
    echo  [ERREUR] PyInstaller a echoue
    pause
    exit /b 1
)

:: -----------------------------------------------
:: Resultat
:: -----------------------------------------------
echo.
echo  ===================================
echo   Build termine avec succes !
echo  ===================================
echo.
echo   Le .exe est dans :
echo   dist\AgentAlternance\AgentAlternance.exe
echo.
echo   Pour distribuer :
echo   1. Copie tout le dossier dist\AgentAlternance\
echo   2. L'utilisateur doit creer un fichier .env
echo      avec sa cle ANTHROPIC_API_KEY
echo   3. Double-clic sur AgentAlternance.exe
echo.
pause
