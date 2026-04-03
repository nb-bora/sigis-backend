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

## Prochaines étapes techniques

1. Brancher SQLAlchemy + PostGIS sous `infrastructure/persistence/`.
2. Implémenter `UnitOfWork` + repositories.
3. Endpoints check-in / validation hôte / check-out en s’appuyant sur les cas d’usage.
