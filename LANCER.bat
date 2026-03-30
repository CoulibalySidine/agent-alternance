@echo off
title Agent Alternance
echo.
echo  ==============================
echo   Agent Alternance - Demarrage
echo  ==============================
echo.

:: Aller dans le dossier du projet
cd /d "%~dp0"

:: Activer le venv
call venv\Scripts\activate

:: Lancer le backend en arriere-plan
echo  Demarrage du backend...
start /min "Backend" cmd /c "venv\Scripts\activate && uvicorn api.main:app --port 8000"

:: Attendre 3 secondes que le backend demarre
timeout /t 3 /nobreak >nul

:: Lancer le frontend en arriere-plan
echo  Demarrage du frontend...
start /min "Frontend" cmd /c "cd frontend && npm run dev"

:: Attendre 3 secondes que le frontend demarre
timeout /t 3 /nobreak >nul

:: Ouvrir le navigateur
echo  Ouverture du navigateur...
start http://localhost:5173

echo.
echo  ================================
echo   L'application est lancee !
echo   Ouvre http://localhost:5173
echo  ================================
echo.
echo  Pour arreter : ferme cette fenetre
echo  (les 2 fenetres minimisees se fermeront aussi)
echo.
pause
taskkill /fi "windowtitle eq Backend" >nul 2>&1
taskkill /fi "windowtitle eq Frontend" >nul 2>&1
