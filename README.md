# 🤖 Agent Alternance

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi)
![Claude](https://img.shields.io/badge/Claude_API-Sonnet_4-blueviolet?logo=anthropic)
![Tests](https://img.shields.io/badge/Tests-29_passed-green?logo=pytest)
![License](https://img.shields.io/badge/License-MIT-yellow)

Agent IA qui automatise toute la chaîne de recherche d'alternance : collecte d'offres, scoring intelligent, génération de candidatures personnalisées, suivi des candidatures.

## ⚡ Démarrage rapide

```bash
# 1. Cloner et installer
git clone https://github.com/CoulibalySidine/agent-alternance.git
cd agent-alternance
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -e ".[dev]"

# 2. Configurer la clé API
cp .env.example .env
# Éditer .env → ANTHROPIC_API_KEY=sk-ant-...

# 3. Lancer l'API
uvicorn api.main:app --reload --port 8000
# → Documentation : http://localhost:8000/docs
```

## 🏗️ Architecture

```
agent-alternance/
├── config.py                  # Configuration centralisée (.env)
├── logger.py                  # Logging structuré (console + fichier)
├── pyproject.toml             # Packaging + dépendances
│
├── api/                       # 🌐 API REST FastAPI (NOUVEAU)
│   ├── main.py                # App, CORS, montage des routers
│   ├── schemas.py             # Modèles Pydantic (validation)
│   ├── tasks.py               # Tâches async en mémoire (scoring, génération)
│   ├── deps.py                # Dépendances partagées (clé API)
│   └── routes/
│       ├── sourcing.py        # GET /offres, POST /offres/scrape
│       ├── qualification.py   # POST /score/{id}, POST /score/batch, GET /tasks/{id}
│       ├── candidature.py     # POST /candidatures/{id}/generer
│       └── suivi.py           # GET /suivi, PATCH /suivi/{id}/etat
│
├── sourcing/                  # Module 1 : Collecte d'offres
│   ├── models.py              # Dataclass Offre (avec champs scoring)
│   ├── runner.py              # Orchestrateur de collecte
│   └── scrapers/              # WTTJ (Algolia), Indeed, Demo
│
├── qualification/             # Module 2 : Scoring IA
│   ├── profil.yaml            # Profil candidat
│   ├── scorer.py              # Prompt engineering + API Claude
│   └── runner.py              # Orchestre le scoring
│
├── candidature/               # Module 3 : Dossiers de candidature
│   ├── generateur.py          # Lettres de motivation (Word + PDF)
│   ├── cv_adapter.py          # CV adapté par offre
│   ├── fiche_entretien.py     # Fiche de préparation entretien
│   ├── reponses_questions.py  # Réponses formulaires personnalisées
│   └── runner.py              # Génère dossier complet
│
├── suivi/                     # Module 4 : Tracking
│   ├── tracker.py             # Machine à états + nettoyage
│   ├── dashboard.py           # Dashboard HTML interactif
│   └── runner.py              # Menu interactif CLI
│
└── tests/                     # 29 tests unitaires
    ├── test_models.py
    ├── test_tracker.py
    └── test_config.py
```

## 🌐 API REST

L'API expose les 4 modules en endpoints REST. Documentation interactive sur `/docs` (Swagger).

### Lancer l'API

```bash
uvicorn api.main:app --reload --port 8000
```

### Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/offres` | Liste des offres (filtres, tri, pagination) |
| `GET` | `/offres/{id}` | Détail d'une offre |
| `POST` | `/offres/scrape` | Lancer un scraping |
| `DELETE` | `/offres/{id}` | Supprimer une offre |
| `POST` | `/score/{id}` | Scorer une offre (async) |
| `POST` | `/score/batch` | Scorer un lot d'offres (async) |
| `GET` | `/tasks/{id}` | État d'une tâche async |
| `POST` | `/candidatures/{id}/generer` | Générer un dossier complet (async) |
| `GET` | `/candidatures/{id}/fichiers` | Lister les fichiers générés |
| `GET` | `/suivi` | Liste du suivi |
| `POST` | `/suivi` | Ajouter une offre au suivi |
| `PATCH` | `/suivi/{id}/etat` | Changer l'état d'une candidature |
| `GET` | `/suivi/stats` | Statistiques du suivi |
| `GET` | `/suivi/dashboard` | Dashboard HTML |
| `GET` | `/health` | Health check |

### Scoring asynchrone

Le scoring et la génération de dossiers sont asynchrones (BackgroundTasks) :

```
POST /score/batch  →  {"task_id": "abc123"}     (200ms)
GET /tasks/abc123  →  {"status": "running", "progress": "3/5 offres scorées"}
GET /tasks/abc123  →  {"status": "done", "result": {...}}
```

### Exemples avec curl

```bash
# Lister les offres scorées au-dessus de 70
curl "http://localhost:8000/offres?score_min=70&tri=score"

# Scraper WTTJ
curl -X POST http://localhost:8000/offres/scrape \
  -H "Content-Type: application/json" \
  -d '{"mot_cle": "alternance développeur", "ville": "Paris"}'

# Scorer les 5 prochaines offres
curl -X POST http://localhost:8000/score/batch \
  -H "Content-Type: application/json" \
  -d '{"max_offres": 5}'

# Générer un dossier de candidature
curl -X POST http://localhost:8000/candidatures/wttj_abc123/generer

# Ajouter au suivi et changer l'état
curl -X POST http://localhost:8000/suivi \
  -H "Content-Type: application/json" \
  -d '{"offre_id": "wttj_abc123"}'

curl -X PATCH http://localhost:8000/suivi/wttj_abc123/etat \
  -H "Content-Type: application/json" \
  -d '{"nouvel_etat": "envoyee", "commentaire": "Envoyé via WTTJ"}'
```

## 🖥️ Usage CLI (modules individuels)

```bash
# Collecter des offres
python -m sourcing.runner

# Scorer les offres
python -m qualification.runner

# Générer les candidatures
python -m candidature.runner

# Dashboard de suivi
python -m suivi.runner
```

## 🛠️ Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.10+ |
| API Web | FastAPI + Uvicorn |
| IA | API Claude (Anthropic) |
| Scraping | Requests + BeautifulSoup + Algolia API |
| Documents | python-docx (Word) + fpdf2 (PDF) |
| Config | .env maison (zéro dépendance) |
| Logging | logging + RotatingFileHandler |
| Tests | pytest (29 tests) |

## 🧪 Tests

```bash
pytest -v
```

## 📊 Exemple de sortie (scoring)

```
🎯 QUALIFICATION — Scoring de 5 offres
============================================================

  [1/5] Développeur Python @ Datadog
    🟢 Score : 85/100 — Très bon match compétences Python + intérêt data

  [2/5] DevOps Junior @ OVHcloud
    🟡 Score : 62/100 — Intérêt cybersécurité mais peu d'XP infra

  [3/5] Data Analyst @ BNP Paribas
    🟡 Score : 58/100 — SQL ok mais manque de stats/R

📊 RÉSULTATS
   Score moyen : 68/100
   Meilleur    : 85/100
```

## 📝 Compétences démontrées

- **API REST** — FastAPI avec validation Pydantic, tâches async, documentation Swagger auto-générée
- **Prompt Engineering** — Scoring sémantique via Claude, format JSON structuré, parsing robuste
- **Architecture logicielle** — 4 modules découplés, pipeline en chaîne, machine à états
- **Web Scraping** — Reverse engineering API Algolia (WTTJ), retry avec backoff exponentiel
- **Génération de documents** — CV Word adapté par offre, lettres PDF, fiches Markdown
- **Qualité de code** — 29 tests, logging structuré, config centralisée, zéro secret en dur

## 📄 License

MIT

---

*Projet réalisé par Sidiné Coulibaly — [GitHub](https://github.com/CoulibalySidine) · [LinkedIn](https://linkedin.com/in/sidiné-coulibaly)*
