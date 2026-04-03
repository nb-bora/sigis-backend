# Architecture SIGIS backend

Alignée sur le cahier **Réflexion SIGIS backend** (DDD + Clean Architecture).

## Dépendances entre couches

```
api  →  application  →  domain
 ↑           ↑
 └───────────┴── infrastructure (implémente les ports de `application`)
```

- **`domain/`** : règles pures, entités, value objects, exceptions métier. **Aucune** dépendance à FastAPI, SQLAlchemy, HTTP.
- **`application/`** : cas d’usage, **ports** (`Protocol`), orchestration. Dépend seulement de `domain`.
- **`infrastructure/`** : settings, persistance PostGIS (à venir), implémentations des repositories / UoW.
- **`api/`** : FastAPI, routes `/v1`, DTO Pydantic, mapping erreurs → HTTP (`common/`).
- **`common/`** : utilitaires transverses (ex. mapping d’erreurs), **sans** logique métier.

## Bounded contexts (V1)

| Contexte              | Paquets domaine principaux                    |
| --------------------- | --------------------------------------------- |
| Référentiel           | `domain.establishment`                        |
| Planification         | `domain.mission`                              |
| Exécution terrain     | `domain.site_visit`, `domain.presence`        |
| Supervision légère    | `domain.exception_request`                    |

Règles transverses : `domain.shared` (géofence, co-présence mode A, `HostValidationMode`).

## Implémentation actuelle (V1)

- **SQLAlchemy 2 async** + **SQLite** (`aiosqlite`) par défaut ; `SIGIS_DATABASE_URL` pour PostgreSQL.
- **`SqlAlchemyUnitOfWork`** + repositories sous `infrastructure/persistence/`.
- **Cas d’usage** : check-in, confirmation hôte (modes A/B/C), check-out, signalement, création établissement/mission.
- **API** : `/v1` — voir `README.md` ; auth dev via `X-User-Id`.
- **Géo** : haversine + deux rayons (pas encore PostGIS SQL).

## Prochaines étapes techniques

1. **Alembic** + migrations ; option **PostGIS** (`ST_DWithin`).
2. **Auth** réelle (JWT) et **RBAC** / visibilité.
3. **Observabilité** : corrélation requêtes, logs d’accès sensibles.
