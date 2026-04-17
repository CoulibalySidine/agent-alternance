@echo off
title Agent Alternance - Build App Release
echo.
echo  =========================================
echo   Agent Alternance - Build Release App
echo   (fenetre native, sans navigateur)
echo  =========================================
echo.

cd /d "%~dp0"

if not exist venv\Scripts\activate (
    echo  [ERREUR] Le venv n'existe pas. Lance d'abord INSTALLER.bat
    pause
    exit /b 1
)

call venv\Scripts\activate

:: Etape 1 : Dependances
echo  [1/3] Installation de PyWebView et PyInstaller...
pip install pywebview pyinstaller pythonnet --quiet
if errorlevel 1 (
    echo  [ERREUR] Impossible d'installer les dependances
    pause
    exit /b 1
)
echo        OK

:: Etape 2 : Build frontend
echo  [2/3] Build du frontend React...
cd frontend
call npm run build
if errorlevel 1 (
    echo  [ERREUR] Le build du frontend a echoue
    cd ..
    pause
    exit /b 1
)
cd ..
echo        OK

:: Etape 3 : Creer le .exe
echo  [3/3] Creation du .exe (3-5 minutes)...
pyinstaller agent-alternance-app.spec --noconfirm
if errorlevel 1 (
    echo  [ERREUR] PyInstaller a echoue
    echo  Si l'erreur concerne pythonnet, utilise
    echo  plutot BUILDER_WEB.bat (plus fiable)
    pause
    exit /b 1
)

echo.
echo  =========================================
echo   Build App termine !
echo  =========================================
echo.
echo   Le .exe est dans :
echo   dist\AgentAlternance\AgentAlternance.exe
echo.
echo   Il ouvre l'appli dans une fenetre native.
echo   Pas de navigateur, pas de console.
echo.
pause
