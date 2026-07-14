# V1 Maturity Score — Analyse de l'écart actuel vs 90/100

**Score ACTUEL**: ~62/100  
**Score CIBLE**: 90/100  
**Gap**: -28 points

---

## 📊 Scoring détaillé (par domaine)

### **A. MÉTIER — 24/40 (60%)**

| Élément | État | Points | Justification |
|---------|------|--------|---|
| **Check-in/out cycle** | ✅ Complet | 8/10 | Implémenté, idempotent, mais pas offline grace |
| **Co-présence 3 modes** | ✅ Codé | 8/10 | A/B/C fonctionnels, B (QR JWT) peu robuste, C (SMS) pas réel |
| **Preuve horodatée + GPS** | ✅ Enregistrée | 6/10 | Enregistrée en DB, mais pas scorée GPS, pas signataire clair |
| **Offline grace timestamps** | ❌ ABSENT | 0/10 | **CRITIQUE**: timestamps serveur seulement, pas client time |
| **Durée minimum visite** | ❌ ABSENT | 2/10 | Check-out possible immédiat après check-in |
| **Hiérarchie validation** | ⚠️ Partiel | 4/10 | Draft/Planned existe, mais pas audit (approver_id, timestamp) |
| **Machine d'états robuste** | ✅ Complète | 6/10 | Transitions formelles existent, mais edge cases manquent |
| **Grace period mission** | ❌ ABSENT | 0/10 | Fenêtre fixe, zéro tolérance avant/après |

**Sous-total MÉTIER**: 24/40 ❌ **-16 points manquants**

**Manques critiques**:
- ❌ Offline grace (client timestamps)
- ❌ Durée minimum visite
- ❌ Grace period mission

---

### **B. SÉCURITÉ ANTI-FRAUDE — 10/20 (50%)**

| Élément | État | Points | Justification |
|---------|------|--------|---|
| **Device binding** | ❌ ABSENT | 0/5 | Zéro implémentation; phone B peut usurper phone A |
| **JTI anti-replay QR** | ⚠️ Partiel | 2/5 | Used_qr_jti table existe (V2 add), mais pas testé exhaustif |
| **Anomaly detection** | ❌ ABSENT | 0/5 | Zéro règles: clone detection, too-short visit, bad GPS, etc. |
| **Audit logs WORM** | ⚠️ Basique | 3/5 | Logs existant, mais pas append-only; modifiables en DB |
| **GPS accuracy scoring** | ❌ ABSENT | 2/5 | accuracy_m pas collectée; impossible détecter spoof |
| **Signature crypto** | ❌ ABSENT | 3/5 | Ed25519 dans cahier, zéro ligne code |

**Sous-total SÉCURITÉ**: 10/20 ❌ **-10 points manquants**

**Manques critiques**:
- ❌ Device binding
- ❌ Anomaly detection rules
- ❌ GPS accuracy collection + scoring

---

### **C. CONFORMITÉ — 6/15 (40%)**

| Élément | État | Points | Justification |
|---------|------|--------|---|
| **DPIA document** | ❌ ABSENT | 0/5 | Zéro document officiel; cahier dit "hors repo" |
| **Rétention policy** | ❌ ABSENT | 0/5 | Pas de cron suppression; données accumulent indéfiniment |
| **Audit logs WORM** | ⚠️ Basique | 3/5 | Logs non-immuables; pas de signature temps |
| **Charte consentement** | ❌ ABSENT | 3/5 | Charte existe (document séparé), pas intégrée app |

**Sous-total CONFORMITÉ**: 6/15 ❌ **-9 points manquants**

**Manques critiques**:
- ❌ DPIA officielle signée
- ❌ Rétention policy + cron
- ❌ Charte intégrée onboarding

---

### **D. UX / ADOPTABILITÉ — 22/25 (88%)**

| Élément | État | Points | Justification |
|---------|------|--------|---|
| **Flow < 15s** | ✅ Probable | 4/5 | Check-in/out simple; probablement < 15s (pas testé) |
| **Offline support** | ⚠️ Partiel | 3/5 | App mobile n'existe pas encore; backend prêt à 70% |
| **French clear errors** | ✅ Bon | 5/5 | Tous messages métier en français, codes typés |
| **Non-blocking fallback** | ⚠️ Conçu | 5/5 | Système pensé pour marcher sans réseau; testé partiellement |
| **Usability testing** | ❌ ABSENT | 0/5 | Zéro test avec inspecteurs réels |

**Sous-total UX**: 22/25 ❌ **-3 points manquants**

**Manques mineurs**:
- ❌ Usability test real inspectors

---

### **E. OBSERVABILITÉ PRODUCTION — 4/15 (27%)**

| Élément | État | Points | Justification |
|---------|------|--------|---|
| **Request ID tracing** | ✅ Implémenté | 4/5 | X-Request-ID middleware présent |
| **Error rate tracking** | ❌ ABSENT | 0/5 | Pas de Prometheus/CloudWatch; CI coverage < logs |
| **API latency SLA** | ❌ ABSENT | 0/5 | Pas de APM; p95 latency inconnu |
| **Data consistency checks** | ❌ ABSENT | 0/5 | Zéro validations périodiques |

**Sous-total OBSERVABILITÉ**: 4/15 ❌ **-11 points manquants**

**Manques critiques**:
- ❌ APM (Prometheus ou équivalent)
- ❌ Error rate alerting
- ❌ Data consistency monitoring

---

## 📈 **Score par acteur**

### **Inspecteur: 65/100** ❌

```
Offline possible:          ⚠️ 50% (app n'existe pas)
Co-présence rapide:        ✅ 90% (métier OK, UX TBD)
Preuve horodatée + GPS:    ✅ 85% (enregistrée, pas scorée)
Messages clairs:           ✅ 95% (français bon)
Pas d'overhead:            ⚠️ 60% (dépend UX mobile)
Battery friendly:          ⚠️ 50% (app TBD)
────────────────────
TOTAL INSPECTEUR:          65/100
```

**Manques**: Offline grace, app mobile, battery optimization

---

### **Responsable accueil: 70/100** ⚠️

```
Mode B (QR no-app):        ✅ 85% (UUID works, JWT TBD)
Mode C (SMS real):         ⚠️ 30% (stubs only, no Twilio)
Co-présence time+distance: ✅ 80% (enregistré, pas affiché user)
Signature non-falsifiable: ⚠️ 60% (possible via device binding V2)
Règles métier formelles:   ✅ 85% (délai/distance codés)
────────────────────
TOTAL ACCUEIL:             70/100
```

**Manques**: SMS réel, signature crypto, UX hôte

---

### **Directeur académie: 55/100** ❌

```
Dashboard temps réel:      ⚠️ 40% (existe, peu riche)
Anomaly alerts:            ❌ 0% (zéro règles)
Arbitrage facile:          ⚠️ 70% (preuve existe, pas UI)
Export CSV:                ✅ 80% (endpoint prêt)
Audit accessible:          ⚠️ 60% (logs exist, no role access)
────────────────────
TOTAL ACADÉMIE:            55/100
```

**Manques**: Anomaly detection, dashboard analytics, anomaly alerts

---

### **Conformité: 40/100** ❌

```
DPIA document:             ❌ 0% (n'existe pas)
Rétention policy:          ❌ 0% (no cron)
Audit WORM:                ⚠️ 50% (partiellement)
Charte consentement:       ⚠️ 60% (document, pas intégré)
────────────────────
TOTAL CONFORMITÉ:          40/100
```

**Manques**: DPIA, rétention, charte intégrée

---

## 🔴 **Les 7 obstacles pour atteindre 90/100**

### **1️⃣ OFFLINE GRACE (client timestamps) — 10 points**
- ❌ **Impact**: Inspecteur offline > fenêtre = visite invalide
- 🎯 **Fix**: Ajouter `captured_at_client` partout (check-in, confirm, checkout)
- ⏱️ **Effort**: 3 jours (schema migration, UC, tests)
- 🚨 **Criticité**: BLOQUANT

### **2️⃣ ANOMALY DETECTION (5+ rules) — 8 points**
- ❌ **Impact**: Fraude invisible; aucune détection automatique
- 🎯 **Fix**: Implémenter dashboard rules (clone, too-short, bad GPS, etc.)
- ⏱️ **Effort**: 4 jours (rules code + tests + dashboard endpoint)
- 🚨 **Criticité**: IMPORTANT

### **3️⃣ DEVICE BINDING (V2 prep, track now) — 8 points**
- ❌ **Impact**: Phone B peut usurper phone A
- 🎯 **Fix**: Ajouter `device_id` + public_key_ed25519 tracking
- ⏱️ **Effort**: 2 jours (schema + UC modification)
- 🚨 **Criticité**: IMPORTANT (V2 crypto later, mais track maintenant)

### **4️⃣ GPS ACCURACY SCORING — 6 points**
- ❌ **Impact**: Impossible détecte GPS spoof
- 🎯 **Fix**: Collecter `accuracy_m`, scorer (EXCELLENT/GOOD/FAIR/POOR)
- ⏱️ **Effort**: 2 jours (schema + UC + audit dashboard)
- 🚨 **Criticité**: IMPORTANT

### **5️⃣ DPIA + CONFORMITÉ — 9 points**
- ❌ **Impact**: Risque légal; non-conforme RGPD/local
- 🎯 **Fix**: Document signé + audit + rétention cron
- ⏱️ **Effort**: 5 jours (DPIA rédaction, cron job, test rétention)
- 🚨 **Criticité**: IMPORTANT (avant prod)

### **6️⃣ APM + OBSERVABILITÉ PROD — 7 points**
- ❌ **Impact**: Incident = aveugle; impossible debug
- 🎯 **Fix**: Prometheus/CloudWatch + latency SLA + alerting
- ⏱️ **Effort**: 3 jours (APM client, dashboards Grafana, alerts)
- 🚨 **Criticité**: IMPORTANT (avant prod)

### **7️⃣ DURÉE MINIMUM VISITE + GRACE PERIOD — 5 points**
- ❌ **Impact**: Check-out immédiat; mission sans tolérance
- 🎯 **Fix**: Min 5 min visite, ±10/15 min grace mission window
- ⏱️ **Effort**: 1 jour (règles métier + tests)
- 🚨 **Criticité**: NORMAL

---

## 🎯 **Roadmap: 62 → 90/100**

### **Phase 1 — CRITIQUES (10 jours)**
```
Jour 1-3:   Offline grace timestamps (client_captured_at)
Jour 2-4:   Device binding v1 (track, prepare for crypto V2)
Jour 4-5:   GPS accuracy scoring (collect + score)
Jour 5-6:   Anomaly detection rules (5+ implémentées)
            → Score: ~78/100
```

### **Phase 2 — CONFORMITÉ (5 jours)**
```
Jour 7-8:   DPIA document + audit cleanup
Jour 8-9:   Rétention cron job
Jour 9-10:  Charte intégrée onboarding
            → Score: ~87/100
```

### **Phase 3 — POLISH (3 jours)**
```
Jour 11:    APM/monitoring setup
Jour 12:    Durée minimum visite + grace period
Jour 13:    Usability test (inspect réels ou simulation)
            → Score: 90+/100
```

**Total: 13 jours (~3 semaines)** pour atteindre 90/100 en métier pur.

---

## ✅ **Checklist pour 90/100**

```
MÉTIER (besoin +16)
☐ Offline grace: client_captured_at utilise (check-in, confirm, checkout)
☐ GPS accuracy: accuracy_m collecté, scoré (EXCELLENT/GOOD/FAIR/POOR)
☐ Device binding v1: device_id + public_key tracé
☐ Durée minimum: 5 min enforced
☐ Grace period: mission window ±10/15 min

SÉCURITÉ (besoin +10)
☐ Anomaly detection: 5+ rules implémentées (clone, too-short, bad GPS, JTI check, etc.)
☐ Audit logs: immuables (append-only ou signature)
☐ JTI anti-replay: testé exhaustif

CONFORMITÉ (besoin +9)
☐ DPIA: document signé + limites V1/V2/V3 documentées
☐ Rétention: cron job automatique (images 30-90j, metadata 1-2y, audit 3y)
☐ Charte: intégrée onboarding, signature tracée

OBSERVABILITÉ (besoin +7)
☐ APM: Prometheus ou CloudWatch (latency p95 < 2s SLA)
☐ Alerting: error rate > 1%, offline queue > 100, DB down
☐ Data consistency: checks périodiques (orphaned records, etc.)

UX (besoin +3)
☐ Usability test: 5-10 inspecteurs réels OU simulation
☐ Performance: check-in < 5s, confirm < 3s, checkout < 3s

DOCUMENTATION
☐ docs/BUSINESS_RULES.md: toutes règles formalisées
☐ docs/SECURITY.md: device binding, anti-replay, anomaly rules
☐ docs/COMPLIANCE.md: DPIA, rétention, charte
```

---

## 🏆 **Victoire: 90/100 signifie**

✅ **Inspecteur** peut faire visite offline, preuve inarguable  
✅ **Hôte** peut valider sans app, co-présence vérifiée  
✅ **Académie** peut voir anomalies, arbitrer disputes  
✅ **Conformité** signé, audit trail, rétention automatique  
✅ **Sécurité** device binding tracé, fraud detection active  
✅ **Observabilité** système en production confiant (< 2s latency, < 1% erreurs)

**= Système prêt V1 pilot, MINESEC/MINSUB peut le deployer en confiance.**

---

*Mis à jour: 2026-07-14*
*Score current: 62/100 → Target: 90/100 (+28 points en 13 jours effort estimé)*
