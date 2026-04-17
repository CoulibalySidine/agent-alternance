@echo off
title Agent Alternance - Build Web Release
echo.
echo  =========================================
echo   Agent Alternance - Build Release Web
echo   (ouvre dans le navigateur)
echo  =========================================
echo.

cd /d "%~dp0"

if not exist venv\Scripts\activate (
    echo  [ERREUR] Le venv n'existe pas. Lance d'abord INSTALLER.bat
    pause
    exit /b 1
)

call venv\Scripts\activate

:: Etape 1 : PyInstaller
echo  [1/3] Installation de PyInstaller...
pip install pyinstaller --quiet
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
echo  [3/3] Creation du .exe (2-3 minutes)...
pyinstaller agent-alternance-web.spec --noconfirm
if errorlevel 1 (
    echo  [ERREUR] PyInstaller a echoue
    pause
    exit /b 1
)

echo.
echo  =========================================
echo   Build Web termine !
echo  =========================================
echo.
echo   Le .exe est dans :
echo   dist\AgentAlternance\AgentAlternance.exe
echo.
echo   Il ouvre l'appli dans le navigateur.
echo   Une petite fenetre console reste ouverte
echo   (c'est le serveur, ne pas la fermer).
echo.
pause
