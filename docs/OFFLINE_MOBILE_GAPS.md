# SIGIS — Gaps offline/mobile (terrain Cameroun)

Ce document liste **précisément** (avec chemins) ce qui manque aujourd'hui dans SIGIS pour une app terrain **offline-first** (React Native), et les risques associés (anti-fraude, sync, QR/SMS).

## Backend (`sigis-backend`) — ce qui existe déjà

### Exécution terrain V1
- **Check-in inspecteur**: `POST /v1/missions/{mission_id}/check-in`
  - Routes: `e:/SIGIS/sigis-backend/api/v1/site_visits.py`
  - UC: `e:/SIGIS/sigis-backend/application/use_cases/check_in_inspector.py`
  - Points clés: géofence + fenêtre mission + idempotency via `client_request_id`

- **Confirmation hôte**: `POST /v1/site-visits/{site_visit_id}/host-confirmation`
  - Route: `e:/SIGIS/sigis-backend/api/v1/site_visits.py`
  - UC: `e:/SIGIS/sigis-backend/application/use_cases/confirm_host_presence.py`
  - Modes:
    - A (app_gps): co-présence (délai + distance) via `e:/SIGIS/sigis-backend/domain/shared/copresence_rules.py`
    - B (QR): token UUID (`host_token`) ou **JWT QR court**
    - C (SMS): comparaison d'un code en base

- **Check-out**: `POST /v1/site-visits/{site_visit_id}/check-out`
  - Route: `e:/SIGIS/sigis-backend/api/v1/site_visits.py`
  - UC: `e:/SIGIS/sigis-backend/application/use_cases/check_out_visit.py`

### QR JWT court (existant)
- Emission: `e:/SIGIS/sigis-backend/common/host_qr_jwt.py` (`create_host_qr_jwt`)
- Vérification: `e:/SIGIS/sigis-backend/common/host_qr_jwt.py` (`verify_host_qr_jwt`)

### Idempotency (existant)
- Repo SQLAlchemy: `e:/SIGIS/sigis-backend/infrastructure/persistence/sqlalchemy/extra_repos.py` (`IdempotencyRepositoryImpl`)
- Limite: **pas de TTL / cleanup**

### Auth JWT + RBAC (existant)
- Dépendances auth/permissions: `e:/SIGIS/sigis-backend/api/deps.py`
- Emission token: `e:/SIGIS/sigis-backend/application/use_cases/auth/login.py`
- Limites: pas de `jti`, pas de refresh/rotation/revocation

### Audit / Telemetry (existant)
- Audit: `e:/SIGIS/sigis-backend/common/audit.py`, lecture/export: `e:/SIGIS/sigis-backend/api/v1/audit.py`
- Telemetry ingestion + buffer mémoire: `e:/SIGIS/sigis-backend/api/v1/telemetry.py`

## Backend — manques critiques pour une app terrain offline-first

### 1) Protocole de sync
- **Manque un endpoint batch** (upload d'une file d'événements offline avec réponse par item).
  - Aujourd'hui: uniquement endpoints unitaires (`check-in`, `host-confirmation`, `check-out`).

- **Manque un endpoint de delta sync** (missions/établissements/visites “nécessaires au terrain” depuis un cursor).
  - Aujourd'hui: listes paginées `GET /missions`, `GET /establishments`, `GET /users` via `PageParams`.

- **Manque une sémantique de conflits / reprise** (état serveur ≠ état client).

### 2) Offline grace / timestamps
- Aujourd'hui, la fenêtre mission est vérifiée avec l'heure serveur “au moment de la requête”.
  - Ex: `verify_host_qr_jwt` (fenêtre mission) dans `e:/SIGIS/sigis-backend/common/host_qr_jwt.py`
  - Conséquence: une action réalisée offline et uploadée plus tard peut être refusée même si elle a eu lieu dans la fenêtre.

### 3) Anti-fraude (GPS + preuves)
- Le backend ne collecte pas de champs “qualité GPS” (`accuracy_m`, provider, etc.) → impossible de scorer des anomalies proprement.
- Pas de “device binding” ni signature cryptographique d'événements offline.

### 4) Anti-replay QR/SMS
- QR UUID statique (`host_token`) est rejouable pendant toute la fenêtre mission.
- QR JWT court **rejouable dans son TTL** (pas de `jti` consommé).
- SMS: pas d'intégration opérateur; validation = comparaison de `missions.sms_code` (stocké).

### 5) Observabilité durable
- Telemetry stockée en mémoire → pas utilisable pour arbitrage/litiges long terme.

## Frontend Admin (`sigis-admin`) — manques

### Auth / stockage
- Token en `sessionStorage`: `e:/SIGIS/sigis-admin/src/lib/auth.tsx`
- API client: `e:/SIGIS/sigis-admin/src/lib/api.ts`

### Offline
- Pas de service worker / IndexedDB / queue persistée.
  - React Query cache = mémoire: `e:/SIGIS/sigis-admin/src/App.tsx`

### Terrain
- Pas de capture caméra / scan QR / géolocalisation terrain.
- Carte Leaflet sert à choisir les coordonnées d'établissements:
  - `e:/SIGIS/sigis-admin/src/components/establishments/MapPickerDialog.tsx`

