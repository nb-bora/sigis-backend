# sigis-backend

Backend **FastAPI** pour **SIGIS** (traçabilité des missions d’inspection scolaire) — structure **DDD** + **Clean Architecture**, conforme au cahier de modélisation métier.

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

## Tests

```bash
pytest
```

## Option PostGIS

```bash
pip install -e ".[db]"
```

Puis modéliser les tables et repositories sous `infrastructure/persistence/`.
