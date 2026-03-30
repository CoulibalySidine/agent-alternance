# Contexte complet du projet Agent Alternance — Résumé de conversation

## Qui je suis
Sidiné COULIBALY, développeur logiciel avec une Licence Informatique de CY Université (2019-2024). Je cherche une alternance de 2 ans (rythme 1 semaine école / 3 semaines entreprise) en développement, data ou cybersécurité en Île-de-France.

## Le projet
Un agent IA complet qui automatise toute la chaîne de recherche d'alternance en 5 modules Python + API REST + Frontend React. Le projet est dans `C:\Users\SidCo\Projets\agent-alternance\` avec un venv Python.

## Architecture actuelle (v1.1.0)

```
agent-alternance/
├── config.py                    # Configuration centralisée (.env)
├── logger.py                    # Logging structuré (console + fichier)
├── .env                         # Clés API (non versionné)
├── .env.example                 # Modèle de config
├── .gitignore                   # Protection des secrets
├── pyproject.toml               # Config projet + dépendances + pytest
├── README.md                    # README pro avec section API complète
├── architecture.png             # Diagramme d'architecture
├── COMPETENCES_CV.md            # Compétences pour CV et entretiens
│
├── profil/                      # Module 0 : Extraction de profil depuis CV — NOUVEAU
│   ├── __init__.py
│   ├── extracteur.py            # Lecture PDF/Word → texte brut (pdfplumber + python-docx)
│   └── generateur_profil.py     # Claude analyse le CV → profil.yaml structuré
│
├── api/                         # API REST FastAPI — NOUVEAU
│   ├── __init__.py
│   ├── main.py                  # App FastAPI, CORS, montage des 5 routers
│   ├── schemas.py               # Modèles Pydantic (validation request/response)
│   ├── tasks.py                 # Gestionnaire de tâches async en mémoire
│   ├── deps.py                  # Dépendances (clé API)
│   └── routes/
│       ├── __init__.py
│       ├── profil.py            # POST /profil/upload, GET/PUT/DELETE /profil
│       ├── sourcing.py          # GET /offres, POST /offres/scrape, DELETE /offres/{id}
│       ├── qualification.py     # POST /score/{id}, POST /score/batch, GET /tasks/{id}
│       ├── candidature.py       # POST /candidatures/{id}/generer, GET fichiers
│       └── suivi.py             # GET /suivi, POST, PATCH état, DELETE, stats, dashboard
│
├── frontend/                    # Frontend React + Vite — NOUVEAU
│   ├── package.json
│   ├── vite.config.js           # Proxy vers FastAPI backend
│   ├── index.html
│   └── src/
│       ├── main.jsx             # Point d'entrée React
│       ├── App.jsx              # Routes : /, /offres, /suivi
│       ├── api.js               # Client API centralisé
│       ├── index.css             # Thème sombre (DM Sans + JetBrains Mono)
│       ├── components/
│       │   ├── Layout.jsx       # Sidebar + health check
│       │   ├── Toast.jsx        # Notifications
│       │   └── TaskBar.jsx      # Barre de progression async
│       └── pages/
│           ├── Onboarding.jsx   # Upload CV + métier + ville → profil
│           ├── Offres.jsx       # Liste, filtres, scoring, génération, scraping modal
│           └── Dashboard.jsx    # Suivi, stats, changement d'état
│
├── sourcing/                    # Module 1 : Collecte d'offres
│   ├── models.py                # Dataclass Offre (avec champs scoring) — CORRIGÉ
│   ├── runner.py                # Orchestrateur de collecte
│   ├── offres.json              # Base de données des offres
│   └── scrapers/
│       ├── base.py              # Classe abstraite + retry/backoff
│       ├── wttj.py              # Scraper WTTJ via API Algolia
│       ├── indeed.py            # Scraper Indeed (HTML)
│       └── demo.py              # Données fictives pour tester
│
├── qualification/               # Module 2 : Scoring IA
│   ├── profil.yaml              # Profil candidat (généré par upload CV)
│   ├── scorer.py                # Prompt engineering + API Claude — CORRIGÉ (max retries, timeout)
│   └── runner.py                # Orchestre le scoring — CORRIGÉ (récupère toutes les données)
│
├── candidature/                 # Module 3 : Dossiers de candidature
│   ├── generateur.py            # Lettres de motivation — CORRIGÉ (max retries, infos depuis profil.yaml)
│   ├── cv_adapter.py            # CV adapté par offre — CORRIGÉ (infos depuis profil.yaml, accents)
│   ├── fiche_entretien.py       # Fiche de préparation entretien
│   ├── reponses_questions.py    # Réponses formulaires personnalisées
│   ├── runner.py                # Génère dossier complet — CORRIGÉ (plus de sys.path.insert)
│   └── lettres/                 # Dossiers générés par entreprise
│
├── suivi/                       # Module 4 : Dashboard de tracking
│   ├── tracker.py               # Machine à états + nettoyage — CORRIGÉ (plus de sys.path.insert)
│   ├── dashboard.py             # Dashboard HTML interactif
│   ├── runner.py                # Menu interactif CLI
│   └── suivi.json               # Base de données du suivi
│
├── tests/                       # Tests unitaires + API — ENRICHI
│   ├── conftest.py              # Fixtures partagées (existantes)
│   ├── test_models.py           # 8 tests : Offre, sérialisation, déduplication
│   ├── test_tracker.py          # 14 tests : machine à états, relance, from_dict
│   ├── test_config.py           # 7 tests : parsing .env, validation
│   ├── test_api_sourcing.py     # 12 tests : GET /offres (filtres, tri), detail, delete — NOUVEAU
│   ├── test_api_suivi.py        # 12 tests : GET/POST/PATCH/DELETE suivi, stats — NOUVEAU
│   └── test_api_system.py       # 7 tests : health, racine, profil GET/PUT — NOUVEAU
│
├── .github/workflows/           # CI/CD — NOUVEAU
│   └── ci.yml                   # Tests auto sur push/PR (Python 3.10-3.12)
│
└── logs/
    └── agent.log
```

## Ce qui a été fait dans cette conversation (session 2)

### 1. Audit des 3 fichiers manquants
- `qualification/scorer.py`, `qualification/runner.py`, `candidature/cv_adapter.py`
- 11 problèmes identifiés (3 critiques, 5 importants, 3 mineurs)

### 2. Corrections des 3 fichiers initiaux
- **Clé API en dur** supprimée de runner.py
- **Récursion infinie** dans scorer.py → max 3 tentatives avec backoff 10s→30s→60s
- **Données de scoring perdues** → runner récupère maintenant raison_score, points_forts, points_faibles, conseil
- **Infos personnelles hardcodées** dans cv_adapter.py → lues depuis profil.yaml
- **sys.path.insert** supprimé (utilise pyproject.toml)
- **Timeout API** ajouté (30s) dans scorer.py et cv_adapter.py
- **Matching projet_star** refait (similarité par mots significatifs, seuil 40%)
- **Accents dans noms de fichiers** → unicodedata.normalize
- Logger uniformisé → `get_logger("module.name")` partout

### 3. Audit croisé complet (tous les fichiers du projet)
- Upload de tous les fichiers restants (candidature/*, suivi/*, sourcing/*, logger.py, config.py)
- 5 problèmes critiques identifiés dans l'API (noms de classes faux, machine à états incompatible, types Candidature vs dict)
- Corrections complètes des routes API

### 4. Backend FastAPI (api/)
- 16 endpoints REST répartis en 5 routers (profil, sourcing, qualification, candidature, suivi)
- Scoring et génération de dossiers **asynchrones** (BackgroundTasks + polling)
- Machine à états du suivi alignée avec tracker.py (7 états : brouillon, envoyee, vue, entretien, acceptee, refusee, sans_reponse)
- TaskManager en mémoire pour le suivi des tâches longues
- Validation des données avec Pydantic
- CORS configuré pour le frontend React
- Health check avec vérification des fichiers et de la clé API
- Documentation Swagger auto-générée sur /docs

### 5. Frontend React + Vite (frontend/)
- 3 pages : Onboarding (upload CV), Offres (liste/filtres/scoring/génération), Suivi (dashboard/stats/état)
- Thème sombre cohérent avec le dashboard HTML existant (DM Sans, JetBrains Mono)
- Client API centralisé (api.js) avec toutes les fonctions
- Composants réutilisables : Layout (sidebar + health check), Toast (notifications), TaskBar (progression async)
- Proxy Vite vers le backend (pas de problème CORS en dev)
- Modal de scraping avec mots-clés et ville personnalisables
- Lignes dépliables pour voir le détail des offres et l'analyse IA

### 6. Module Profil (profil/)
- `extracteur.py` : lecture de CV en PDF (pdfplumber), Word (python-docx), ou texte
- `generateur_profil.py` : Claude analyse le texte du CV et génère un profil.yaml structuré
- Endpoint `POST /profil/upload` : upload fichier + métier + ville → profil.yaml
- Page frontend Onboarding : drag & drop, formulaire métier/ville, visualisation et édition du profil

### 7. Dataclass Offre enrichie (sourcing/models.py)
- 4 champs ajoutés : `raison_score`, `points_forts`, `points_faibles`, `conseil`
- `to_dict()` (via asdict) et `from_dict()` (via __dataclass_fields__) fonctionnent automatiquement

### 8. Corrections candidature/ et suivi/
- `generateur.py` : récursion infinie corrigée (max retries), infos perso depuis profil.yaml, timeout API
- `candidature/runner.py` : sys.path.insert supprimé, noms de fichiers safe
- `suivi/tracker.py` : 6 occurrences de sys.path.insert supprimées, import shutil centralisé

### 9. pyproject.toml + README + .env.example
- Version 1.1.0
- Dépendances ajoutées : fastapi, uvicorn[standard], pdfplumber, httpx (dev)
- Package `api*` et `profil*` ajoutés
- README avec section API complète (endpoints, exemples curl, scoring async)
- Badge FastAPI ajouté

### 10. Tests API (tests/)
- 31 nouveaux tests pour les endpoints API
- test_api_sourcing.py : filtres, tri, pagination, détail, suppression (12 tests)
- test_api_suivi.py : liste, stats, ajout, changement d'état, suppression (12 tests)
- test_api_system.py : health, racine, profil (7 tests)
- Total projet : 29 + 31 = 60 tests

### 11. CI/CD GitHub Actions
- `.github/workflows/ci.yml`
- Tests automatiques sur push et PR (branche main)
- Matrice Python 3.10, 3.11, 3.12
- Vérifie les imports critiques

## Dépendances installées
```
pip install requests beautifulsoup4 anthropic python-docx fpdf2 pyyaml pytest fastapi uvicorn pdfplumber httpx
```

## Flux utilisateur complet
```
1. Upload CV (PDF/Word) + poste recherché + ville
   → Claude analyse → profil.yaml généré
   
2. Scraper des offres (WTTJ) par mot-clé + ville
   → offres.json enrichi
   
3. Scorer les offres (API Claude)
   → score 0-100 + analyse (points forts/faibles, conseil)
   
4. Générer les dossiers (CV adapté + lettre + fiche entretien + réponses)
   → fichiers Word/PDF/Markdown dans candidature/lettres/
   
5. Suivi des candidatures
   → machine à états (brouillon → envoyée → entretien → acceptée)
   → alertes de relance automatiques
```

## Points restants (prochaines sessions)
- Ajouter de nouveaux scrapers (LinkedIn, Hellowork, France Travail)
- Candidature automatique (envoi direct sur les sites)
- Base de données (SQLite/PostgreSQL) pour remplacer les fichiers JSON
- Multi-utilisateur (comptes, sessions, profils séparés)
- Déploiement cloud (Railway, Render, ou VPS)
- Tests d'intégration (avec mock de l'API Claude)
