# sigis-backend

[![CI](https://github.com/nb-bora/sigis-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/nb-bora/sigis-backend/actions/workflows/ci.yml)

Backend **FastAPI** pour **SIGIS** (traçabilité des missions d’inspection scolaire) — structure **DDD** + **Clean Architecture**, conforme au cahier de modélisation métier.

## Intégration continue (CI/CD)

| Élément | Rôle |
|--------|------|
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | **GitHub Actions** : Ruff (lint + format vérifié) puis **pytest** sur Python **3.11** et **3.12** à chaque push / PR vers `main` |
| [`.github/dependabot.yml`](.github/dependabot.yml) | **Dependabot** : mises à jour hebdomadaires (pip) et mensuelles (actions) |
| [`.pre-commit-config.yaml`](.pre-commit-config.yaml) | Hooks **Ruff** optionnels en local (`pip install pre-commit && pre-commit install`) |

Exécution manuelle possible dans l’onglet **Actions** → workflow **CI** → **Run workflow**.

## Arborescence

```
sigis-backend/
├── domain/                    # Règles métier pures (invariants, agrégats, VOs)
│   ├── shared/                # Géofence, co-présence mode A, enums communs
│   ├── establishment/         # Bounded context : Référentiel
│   ├── mission/               # Planification
│   ├── site_visit/            # Exécution terrain
│   ├── presence/              # PresenceProof, CoPresenceEvent
│   └── exception_request/     # Signalements V1 (supervision légère)
├── application/               # Cas d'usage + ports (interfaces)
│   ├── ports/                 # Repositories, Unit of Work
│   └── use_cases/             # Un fichier par flux métier
├── infrastructure/            # Config, persistance PostGIS (à brancher)
│   ├── config/
│   └── persistence/
├── api/                       # FastAPI — routes minces
│   ├── main.py                # create_app(), CORS, prefix /v1
│   └── v1/
├── common/                    # Mapping erreurs HTTP, transversal
├── docs/                      # ADR, glossaire importé, architecture
└── tests/
```

## Installation

```bash
cd sigis-backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

## Lancer l’API

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- Santé : `GET http://localhost:8000/v1/health`
- OpenAPI : `http://localhost:8000/docs`

### Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `SIGIS_DATABASE_URL` | `sqlite+aiosqlite:///./sigis.db` | SQLite async (dev) ; production : `postgresql+asyncpg://...` |
| `SIGIS_API_PREFIX` | `/v1` | Préfixe API |
| `SIGIS_CORS_ORIGINS` | `http://localhost:3000` | CORS |

### Auth développement

En-tête **`X-User-Id`** : UUID de l’utilisateur (inspecteur / hôte). Sans en-tête, un UUID par défaut est utilisé (tests uniquement).

### Endpoints V1 (principaux)

- `POST /v1/establishments` — créer un établissement (point + deux rayons)
- `POST /v1/missions` — créer une mission (retourne `host_token` pour QR / SMS)
- `POST /v1/missions/{id}/check-in` — check-in inspecteur (`host_validation_mode`: `app_gps` \| `qr_static` \| `sms_shortcode`)
- `POST /v1/site-visits/{id}/host-confirmation` — validation hôte (GPS + QR ou SMS selon mode)
- `POST /v1/site-visits/{id}/check-out` — clôture (durée check-in → check-out)
- `POST /v1/missions/{id}/exception-requests` — signalement terrain

Idempotence : champ `client_request_id` (≥ 8 caractères) sur check-in / confirmation / check-out.

## Tests

```bash
pytest
```

(`tests/conftest.py` force `SIGIS_DATABASE_URL` vers `sigis_test.db`.)

## Écarts vs cahier complet

Voir [docs/GAP_IMPLEMENTATION.md](docs/GAP_IMPLEMENTATION.md).

## Option PostgreSQL + PostGIS

```bash
pip install -e ".[postgres]"
```

Configurer `SIGIS_DATABASE_URL` et remplacer progressivement le calcul haversine par des requêtes `ST_DWithin` (migrations Alembic recommandées).
