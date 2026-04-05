# sigis-backend

[![CI](https://github.com/nb-bora/sigis-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/nb-bora/sigis-backend/actions/workflows/ci.yml)

**API HTTP** du **Système d’Information de traçabilité des missions d’inspection scolaire (SIGIS)** — contexte **Cameroun** (MINESEC / MINSUB et déconcentration). Ce dépôt expose le **backend** : **FastAPI**, persistance **SQLAlchemy async**, architecture **DDD** et **Clean Architecture**, aligné sur le cahier de modélisation métier du projet.

---

## Table des matières..

1. [Contexte et objectifs](#contexte-et-objectifs)
2. [Ce que fait ce backend (périmètre V1)](#ce-que-fait-ce-backend-périmètre-v1)
3. [Stack technique](#stack-technique)
4. [Architecture logicielle](#architecture-logicielle)
5. [Structure du dépôt](#structure-du-dépôt)
6. [Installation](#installation)
7. [Exécution locale](#exécution-locale)
8. [Configuration](#configuration)
9. [API REST (`/v1`)](#api-rest-v1)
10. [Modes de validation hôte](#modes-de-validation-hôte)
11. [Idempotence et robustesse](#idempotence-et-robustesse)
12. [Qualité : tests, lint, CI](#qualité--tests-lint-ci)
13. [Documentation complémentaire](#documentation-complémentaire)
14. [Limites et suite (V2+)](#limites-et-suite-v2)

---

## Contexte et objectifs

Les inspections scolaires doivent pouvoir s’appuyer sur une **preuve structurée** : **qui** est sur le terrain, **où**, **quand**, et pendant **combien de temps**, avec une **double validation** (inspecteur et responsable d’accueil) lorsque le mode le permet, sans réduire le dispositif à un simple « pointage » opposable.

**SIGIS** vise à :

- centraliser des **événements de présence** vérifiables (géofence, co-présence, durée) ;
- respecter le **réalisme terrain** (réseaux faibles, téléphones hétérogènes, **fallbacks** QR / SMS pour le responsable) ;
- préparer une **gouvernance des données** (charte, visibilité, pas de sanction automatique par l’outil seul) — aspects surtout **hors code**, documentés dans le cahier projet.

Ce backend matérialise la **couche V1 pilote** : **présence vérifiable** et **mini-workflow de signalement** ; la **richesse métier** type rapport de visite structuré (`MissionOutcome`) est **hors périmètre V1** (prévue en V2).

---

## Ce que fait ce backend (périmètre V1)

| Domaine | Fonctionnalité |
|--------|----------------|
| **Référentiel** | Création d’**établissements** avec centre géographique et **deux rayons** (strict / élargi) pour les statuts OK / probable / hors zone. |
| **Planification** | Création de **missions** (fenêtre horaire, inspecteur, lien établissement), génération d’un **`host_token`** pour les parcours QR. |
| **Exécution terrain** | **Check-in** inspecteur, **confirmation hôte** selon le mode (GPS, QR, SMS), **check-out**, calcul d’une **durée de présence** (check-in → check-out). |
| **Preuves** | Enregistrement de **preuves de présence** et d’**événements de co-présence** lorsque les règles sont satisfaites. |
| **Supervision légère** | **Signalements** liés à une mission (périmètre faux, incident, etc.). |
| **Technique** | **Idempotence** sur les actions sensibles via `client_request_id`, erreurs métier **typées** (`DomainError` → HTTP). |

La géolocalisation est calculée **côté application** (haversine + seuils). **PostGIS** en base est une **évolution** prévue (voir [Limites et suite](#limites-et-suite-v2)).

---

## Stack technique

| Composant | Choix |
|-----------|--------|
| Langage | **Python ≥ 3.11** |
| Framework HTTP | **FastAPI** |
| Validation / schémas | **Pydantic v2** |
| Persistance | **SQLAlchemy 2** (async), **SQLite** + `aiosqlite` par défaut |
| Tests | **pytest**, **httpx** (TestClient) |
| Lint / format | **Ruff** |
| CI | **GitHub Actions** (voir [Qualité](#qualité--tests-lint-ci)) |

---

## Architecture logicielle

Les règles métier vivent dans **`domain/`** (invariants, agrégats, value objects). Les **cas d’usage** orchestrent dans **`application/`**. Les adaptateurs (ORM, configuration) sont dans **`infrastructure/`**. Les routes HTTP et DTO sont dans **`api/`**.

```
api  →  application  →  domain
 ↑           ↑
 └───────────┴── infrastructure (repositories, UoW, session)
```

Détail des **bounded contexts**, ports et conventions : **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Structure du dépôt

```
sigis-backend/
├── domain/                 # Règles pures (géofence, co-présence, transitions SiteVisit, modes hôte)
├── application/            # Cas d’usage (check-in, confirmation hôte, check-out, missions, signalements)
├── infrastructure/       # Settings, SQLAlchemy, Unit of Work, repositories
├── api/                    # FastAPI — `main.py`, `v1/` (routes, schémas)
├── common/                 # Utilitaires transverses (ex. mapping erreurs HTTP)
├── docs/                   # Architecture, écarts vs cahier complet
├── tests/                  # Tests unitaires et flux E2E
├── .github/workflows/      # CI
└── pyproject.toml
```

---

## Installation

**Prérequis** : Python **3.11** ou **3.12**, `git`.

```bash
git clone <url-du-depot>
cd sigis-backend
python -m venv .venv
```

**Windows (PowerShell)** :

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**Linux / macOS** :

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

Dépendances optionnelles :

- **`[postgres]`** : `asyncpg`, `geoalchemy2` pour un déploiement PostgreSQL / PostGIS.

Le projet épingle **bcrypt avant la 4.1** : les versions 4.1 et suivantes de la librairie `bcrypt` ne sont pas compatibles avec **passlib** 1.7.x (échec ou **500** sur `POST /v1/auth/login` lors du hachage ou de la vérification). Après `git pull`, relancer `pip install -e ".[dev]"` pour réaligner l’environnement.

---

## Exécution locale

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

| Ressource | URL |
|-----------|-----|
| Santé | `GET http://localhost:8000/v1/health` |
| OpenAPI (Swagger) | `http://localhost:8000/docs` |
| Schéma OpenAPI JSON | `http://localhost:8000/openapi.json` |

Au premier démarrage, les **tables** sont créées automatiquement (`create_all`) — adapté au **développement**. En production, prévoir des **migrations** (ex. Alembic).

---

## Configuration

Variables d’environnement (préfixe **`SIGIS_`**, voir `.env.example`) :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `SIGIS_DATABASE_URL` | `sqlite+aiosqlite:///./sigis.db` | SQLite async en dev ; en prod : `postgresql+asyncpg://user:pass@hôte:5432/base` |
| `SIGIS_API_PREFIX` | `/v1` | Préfixe des routes API |
| `SIGIS_CORS_ORIGINS` | `http://localhost:3000`, `https://sigis-lime.vercel.app` | Origines CORS autorisées (liste séparée par des virgules) |
| `SIGIS_DATABASE_ECHO` | `false` | Journaliser les requêtes SQL (debug) |

---

## API REST (`/v1`)

Toutes les routes ci-dessous sont préfixées par `SIGIS_API_PREFIX` (par défaut **`/v1`**).

| Méthode | Chemin | Description |
|---------|--------|-------------|
| `GET` | `/health` | Indicateur de disponibilité |
| `POST` | `/establishments` | Créer un établissement (nom, centre lat/lon, deux rayons en mètres) |
| `POST` | `/missions` | Créer une mission ; réponse inclut `mission_id` et `host_token` |
| `POST` | `/missions/{mission_id}/check-in` | Check-in inspecteur (position, mode de validation hôte) |
| `POST` | `/missions/{mission_id}/exception-requests` | Créer un signalement terrain |
| `POST` | `/site-visits/{site_visit_id}/host-confirmation` | Valider la présence côté hôte (selon le mode choisi au check-in) |
| `POST` | `/site-visits/{site_visit_id}/check-out` | Clôturer la visite (durée dérivée du check-in / check-out) |

**Authentification (développement)** : en-tête **`X-User-Id`** avec un UUID (inspecteur ou hôte). Sans en-tête, un UUID par défaut est utilisé (pratique limitée aux tests).

---

## Modes de validation hôte

Le champ `host_validation_mode` au **check-in** fixe le scénario pour la **confirmation hôte** :

| Mode | Valeur API | Idée métier |
|------|------------|-------------|
| **A** | `app_gps` | Deux positions GPS : co-présence (délai + distance) entre inspecteur et hôte. |
| **B** | `qr_static` | Jeton **`host_token`** (mission) présenté via QR / saisie ; cohérence avec la fenêtre de mission. |
| **C** | `sms_shortcode` | Code SMS **configuré sur la mission** (`sms_code` à la création) ; même logique de fenêtre. |

Les invariants détaillés et les limites produit sont dans le **cahier SIGIS** et dans le code (`domain.shared`, `domain.site_visit`).

---

## Idempotence et robustesse

Les actions **check-in**, **host-confirmation** et **check-out** acceptent un champ **`client_request_id`** (min. 8 caractères). Une même clé pour un même **scope** métier renvoie la **réponse** déjà enregistrée — utile pour les **retries** et une future **sync offline** côté client (le détail UX offline n’est pas dans ce dépôt).

---

## Qualité : tests, lint, CI

| Outil | Rôle |
|-------|------|
| `pytest` | Tests dans `tests/` (dont flux E2E minimal en mode `app_gps`) |
| `ruff check` / `ruff format` | Lint et formatage |
| [`.pre-commit-config.yaml`](.pre-commit-config.yaml) | Hooks Ruff optionnels en local (`pre-commit install`) |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI : Ruff puis pytest sur Python **3.11** et **3.12** |
| [`.github/dependabot.yml`](.github/dependabot.yml) | Mises à jour dépendances pip et GitHub Actions |

```bash
pytest
ruff check .
ruff format --check .
```

Les tests fixent `SIGIS_DATABASE_URL` vers une base fichier dédiée (`tests/conftest.py`).

---

## Documentation complémentaire

| Document | Contenu |
|----------|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Couches, bounded contexts, dépendances |
| [docs/GAP_IMPLEMENTATION.md](docs/GAP_IMPLEMENTATION.md) | Ce qui est **volontairement** hors périmètre ou à renforcer (PostGIS, auth prod, RBAC, V2, etc.) |

Le **cahier de cadrage métier** (roadmap V1/V2/V3, gouvernance, charte) est tenu **en dehors** de ce dépôt (Cursor plan / document projet).

---

## Limites et suite (V2+)

- **Pas** de `MissionOutcome` / rapport de visite riche en V1 (prévu V2).
- **Pas** d’authentification OAuth/JWT ni de **RBAC** complet en production dans la version actuelle.
- **PostGIS** (`ST_DWithin`, géométrie versionnée en SQL) **non** requis pour faire tourner le projet ; **Alembic** recommandé pour les migrations une fois le schéma stabilisé.
- Liste exhaustive des écarts par rapport au cahier : **[docs/GAP_IMPLEMENTATION.md](docs/GAP_IMPLEMENTATION.md)**.

---

*SIGIS — preuve structurée de présence et de cohérence terrain ; pilotage institutionnel et acceptabilité sociale documentés dans le cahier projet.*
