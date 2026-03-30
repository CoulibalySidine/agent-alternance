@echo off
title Agent Alternance - Installation
echo.
echo  ===================================
echo   Agent Alternance - Installation
echo  ===================================
echo.

cd /d "%~dp0"

:: Verifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Python n'est pas installe.
    echo  Telecharge-le ici : https://www.python.org/downloads/
    echo  IMPORTANT : coche "Add Python to PATH" pendant l'installation
    pause
    exit /b 1
)
echo  [OK] Python detecte

:: Verifier Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Node.js n'est pas installe.
    echo  Telecharge-le ici : https://nodejs.org/
    pause
    exit /b 1
)
echo  [OK] Node.js detecte

:: Creer le venv
echo.
echo  Creation de l'environnement Python...
python -m venv venv
call venv\Scripts\activate

:: Installer les dependances Python
echo  Installation des dependances Python...
pip install -e ".[dev]" --quiet
pip install pdfplumber --quiet
echo  [OK] Dependances Python installees

:: Installer le frontend
echo  Installation du frontend...
cd frontend
call npm install --silent
cd ..
echo  [OK] Frontend installe

:: Creer le .env si il n'existe pas
if not exist .env (
    copy .env.example .env >nul
    echo.
    echo  ===================================
    echo   IMPORTANT : Configure ta cle API
    echo  ===================================
    echo.
    echo  1. Va sur https://console.anthropic.com
    echo  2. Cree un compte et genere une cle API
    echo  3. Ouvre le fichier .env avec le Bloc-notes
    echo  4. Remplace "sk-ant-ta-cle-ici" par ta vraie cle
    echo.
    notepad .env
) else (
    echo  [OK] Fichier .env deja present
)

echo.
echo  ===================================
echo   Installation terminee !
echo   Double-clic sur LANCER.bat
echo   pour demarrer l'application.
echo  ===================================
echo.
pause
