# SIGIS — Paquet de preuve mobile (open-source, offline-first)

Ce document définit le **paquet de preuve** attendu d'une application terrain (React Native), en contexte **Cameroun** (réseau instable, data chère, téléphones modestes), tout en restant **100% open-source**.

## Objectifs

- **Intégrité**: empêcher la modification “après coup” d’un événement offline.
- **Attribution**: lier un événement à un device connu (clé publique).
- **Plausibilité**: enregistrer la qualité GPS pour scorer des anomalies.
- **Sobriété**: payload compact + compression; ne pas drainer la batterie.
- **Vie privée**: capturer le strict minimum; rétention courte des médias.

## Structures (résumé)

Les schémas sont implémentés côté API dans `e:/SIGIS/sigis-backend/api/v1/schemas.py`:
- `MobileEventIn`
- `MobileGps`
- `MobileMediaSelfie`

### 1) GPS

Champs requis (si policy active):
- `lat`, `lon`
Champs recommandés:
- `accuracy_m` (float, mètres)
- `provider` (ex: `gps`, `network`, `fused`)

### 2) Média (selfie)

MVP: le backend ne transporte pas encore le binaire; il référence:
- `sha256` (hash hex du fichier)
- `mime`, `w`, `h`

## Signature / hash chain (anti-tamper offline)

### Identités

- Chaque device génère une paire de clés **Ed25519** localement.
- La clé publique (`device_public_key`) est envoyée avec chaque event.
- Le backend associe la première clé vue au device (`mobile_devices.public_key_ed25519`) et refuse si elle change.

### Hashing

- `event_hash`: SHA-256 hex du “canonical payload” (JSON canonique).
- `prev_event_hash`: hash du précédent event du device (chaîne).
- La signature Ed25519 porte sur `event_hash`.

### Canonical payload (recommandation)

- JSON trié par clés, encodage UTF-8, sans espaces inutiles.
- Inclure au minimum: `event_id`, `type`, `mission_id`, `site_visit_id`, `actor_user_id`,
  `device_id`, `client_request_id`, `captured_at_client`, `gps`, `selfie`, `prev_event_hash`.

## Liveness (open-source)

Objectif: réduire la fraude “photo d'écran / photo imprimée”.

Recommandation terrain (téléphones modestes):
- Challenge simple (2 étapes max): cligner + tourner la tête
- Évaluer avec landmarks (MediaPipe Face Mesh ou équivalent open-source)
- Stocker côté event un résumé non sensible (ex: `liveness_passed: true`, `challenge_id`, `score`), pas la vidéo brute.

## Rétention / conformité (pragmatique)

- Images: 30–90 jours (paramétrable) puis purge.
- Conserver durablement: hashes, métadonnées, décisions et raisons.

