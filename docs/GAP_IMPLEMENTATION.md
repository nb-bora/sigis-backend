# Écart restant vs cahier SIGIS (état après implémentation V1 code)

Ce document liste ce qui **n’est pas** couvert ou seulement **partiellement** couvert par rapport à [`réflexion_sigis_backend_7b836ebe.plan.md`](c:\Users\Nanyang Brice\.cursor\plans\réflexion_sigis_backend_7b836ebe.plan.md).

## Implémenté dans le code (V1 technique)

- Couches **DDD** : `domain/` (règles, transitions, modes A/B/C), `application/` (cas d’usage), `infrastructure/` (SQLAlchemy async, SQLite dev / PostgreSQL possible), `api/` (FastAPI `/v1`).
- **Géofence** : deux seuils + haversine (équivalent métier à PostGIS pour la distance point-centre ; pas `ST_DWithin` en SQL).
- **Co-présence mode A** : délai + distance ; modes **B/C** : jeton QR + code SMS + fenêtre mission.
- **Persistance** : missions, établissements, visites, preuves, événements co-présence, signalements, **idempotence** basique (clé client par scope).
- **API** : création établissement / mission, check-in, confirmation hôte, check-out, signalement.
- **Tests** : règles géofence + santé + **flux E2E** minimal (mode A).

## Non implémenté ou partiel (à prévoir)

### Produit / institution (hors repo ou document séparé)

- **Glossaire métier V1** figé (document autonome).
- **Charte** 2–3 pages, **sponsoring** SG, **annexe données personnelles**, **arbitrage terrain / SLA** opérationnels.
- **Ground truthing** budgété, **pilote micro** (1 académie, 30–50 établissements), **ambassadeurs**, **formation**.
- **UX mobile** : bandeau offline, sync, **historique local** (côté clients, pas ce backend seul).

### Backend / technique

- **PostGIS** : géométrie stockée + `ST_DWithin` / index spatiaux ; actuellement **lat/lon + rayon** et calcul applicatif.
- **Alembic** : migrations versionnées (actuellement `create_all` au démarrage).
- **Authentification réelle** : JWT / OIDC ; actuellement header dev **`X-User-Id`**.
- **RBAC / visibilité** : qui voit quoi (agrégats, exports) ; **logs d’accès** nominatifs ; **KPI hiérarchie** légers.
- **MissionOutcome (V2)** : volontairement absent.
- **ExceptionWorkflow complet (V2)** : seulement **mini** signalement V1.
- **Anti-replay avancé, DeviceContext riche, audit WORM / hash (V3)** : absents.
- **Idempotence** : pas de reprise de **réponse stockée** en cas de collision concurrente (race) ; pas de **conflit** sync offline modélisé côté serveur au-delà de la clé.
- **Observabilité** : pas de corrélation `request_id` systématique, pas de métriques Prometheus, pas d’export audit WORM.
- **SMS / USSD réels** : pas d’intégration opérateur ; validation **code en base** seulement.
- **QR** : validation **UUID** `host_token` ; pas de **JWT signé** ni QR dynamique (V2).
- **ResponsibleAccueil / délégation** : pas de règle métier « qui peut valider hôte » (tout utilisateur avec `X-User-Id` peut confirmer en mode A).
- **Versionnement géométrie** : champ `geometry_version` sans workflow de correction ni SLA.
- **Tests** : pas de suite contre **PostgreSQL** + PostGIS ; pas de charge / perf.

### Dette qualité

- Durées / datetimes : normalisation **UTC** progressive ; SQLite peut renvoyer des naïfs selon drivers — le code défensif `_aware` limite les écarts.
- **OpenAPI** : erreurs métier via handler `DomainError` ; pas de schéma d’erreur unique référencé partout.

---

**Conclusion** : le dépôt couvre un **MVP technique V1** aligné sur le flux principal du cahier ; il ne remplace **pas** les livrables institutionnels, la **sécurité production**, ni les **phases V2/V3** du plan.
