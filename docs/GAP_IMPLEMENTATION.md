# Écart restant vs cahier SIGIS (état après implémentation V1 code)

Ce document liste ce qui **n’est pas** couvert ou seulement **partiellement** couvert par rapport au plan produit / institutionnel, et ce qui est **désormais en place** dans le dépôt.

## Implémenté dans le code (mis à jour)

- Couches **DDD** : `domain/` (règles, transitions, modes A/B/C), `application/` (cas d’usage), `infrastructure/` (SQLAlchemy async, SQLite dev / PostgreSQL possible), `api/` (FastAPI `/v1`).
- **Authentification** : **JWT** avec **RBAC** (permissions en base, surcharges par rôle). L’en-tête **`X-User-Id`** n’est qu’un raccourci **développement** lorsque `SIGIS_ENV=development` (pas un mode production).
- **Migrations Alembic** : migrations versionnées ; en CI on exécute `alembic upgrade head`. Le **`create_all`** au démarrage reste une option **dev/tests** via `SIGIS_AUTO_CREATE_TABLES=true`.
- **Géofence** : deux seuils + haversine (équivalent métier à PostGIS pour la distance point-centre ; pas `ST_DWithin` en SQL).
- **Co-présence** : mode A (délai + distance) ; modes B/C : jeton QR + code SMS + fenêtre mission ; **JWT QR court** optionnel (`GET /missions/{id}/host-qr-jwt`, validation via `qr_jwt` en confirmation hôte).
- **Hôte désigné** : `designated_host_user_id` sur établissement et/ou mission — seul cet utilisateur peut confirmer la co-présence si renseigné.
- **Mission** : statut `draft`, validation hiérarchique (`POST .../approve`), annulation avec motif (`POST .../cancel`), réaffectation inspecteur (`POST .../reassign`), **MissionOutcome** (`POST/GET .../outcome`).
- **Signalements** : assignation, commentaire interne, SLA léger (`PATCH /exception-requests/{id}`), pièce jointe par URL.
- **Pagination** : listes missions, établissements, utilisateurs, signalements (paramètres `skip` / `limit`).
- **Exports & pilotage léger** : `GET /reports/summary`, `GET /reports/missions.csv` (permission `REPORT_READ`).
- **Audit applicatif** : `GET /audit-logs` (permission `AUDIT_READ`), écritures sur actions clés (validation / annulation / rapport / patch signalement).
- **Observabilité transverse** : **`X-Request-ID`** (middleware), réponses d’erreur métier enrichies avec `request_id` ; schéma OpenAPI **`ErrorResponse`**.
- **Sécurité** : **throttling** sur `POST /auth/login` (paramètre `SIGIS_LOGIN_RATE_LIMIT_PER_MINUTE`).
- **Notifications métier** : stubs dans `common/business_notifications.py` (logs structurés — à brancher sur SMTP ou file de jobs).

## Non implémenté ou partiel (à prévoir)

### Produit / institution (hors repo ou document séparé)

- **Glossaire métier V1** figé (document autonome).
- **Charte** 2–3 pages, **sponsoring** SG, **annexe données personnelles**, **arbitrage terrain / SLA** opérationnels documentés hors code.
- **Ground truthing** budgété, **pilote micro**, **ambassadeurs**, **formation**.
- **UX mobile** : bandeau offline, sync, **historique local** (côté clients, pas ce backend seul).
- **Consentement / DPIA / traçabilité DPIA** : hooks légaux complets (ici : audit technique minimal, pas de registre de traitement intégré).

### Backend / technique

- **PostGIS** : géométrie stockée + `ST_DWithin` / index spatiaux ; actuellement **lat/lon + rayon** et calcul applicatif.
- **Référentiel géographique officiel** : pas d’import de polygones administratifs (champ `territory_code` libre).
- **Hiérarchie territoriale** : codes texte + filtrage ; pas de modèle relationnel région / académie / délégation normalisé.
- **SMS / USSD réels** : pas d’intégration opérateur ; validation **code en base** + stubs de notification.
- **Anti-replay avancé**, **DeviceContext riche**, **audit WORM / chaîne hashée (V3)** : absents (journal applicatif classique).
- **Multi-tenant** : un tenant logique.
- **Tests** : pas de suite systématique **PostgreSQL** en CI ; pas de tests de charge.
- **Observabilité production** : pas de métriques **Prometheus** ni **APM** complet (hors `request_id`).

### Dette qualité

- Durées / datetimes : normalisation **UTC** progressive ; SQLite peut renvoyer des naïfs selon drivers — le code défensif `_aware` limite les écarts.
- **KPI** : agrégations en mémoire sur `/reports/summary` — à optimiser (SQL agrégé) pour très gros volumes.

---

**Conclusion** : le dépôt couvre un **MVP technique V1** enrichi (workflow mission, rapport, audit, exports légers, QR JWT, pagination) ; il ne remplace **pas** les livrables institutionnels, la **sécurité production complète**, ni les **phases V2/V3** du plan (WORM, PostGIS, observabilité complète).
