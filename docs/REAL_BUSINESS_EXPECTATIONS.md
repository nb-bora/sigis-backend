# SIGIS — Attentes métier réelles (objectifs mesurables)

*Analyse des véritables besoins des acteurs terrain + institution, extraits du cahier SIGIS et du contexte Cameroun (MINESEC/MINSUB).*

---

## 🏛️ **Acteurs et leurs attentes réelles**

### **1. INSPECTEUR SCOLAIRE** (terrain)

#### **Qui?**
- Cadre moyens (35-65 ans), peu familier tech
- Supervise écoles/collèges dans zone académique
- Contrôle pédagogie, infrastructure, staff

#### **Vrais problèmes (douleurs)**
| Problème | Contexte | Impact |
|----------|----------|--------|
| **Preuve contestée** | Responsable d'école conteste visite: "tu n'es jamais venu" | Impuissance; rapport faible légalement |
| **Réseaux faibles** | Pas de 3G/4G fiable; mode avion = norme | App online-only = inutile |
| **Batterie téléphone** | Téléphone bas de gamme, 1 journée max | App gourmande = rejet |
| **Perte temps bureaucratie** | Remplir papier + saisir données = 2x travail | Refus adoption si overhead > bénéfice |
| **Surveillance perçue** | Crainte données utilisées contre lui (sanction) | Non-confiance dans l'outil |

#### **Attentes objectives**
1. ✅ **Preuve opposable rapidement**
   - Check-in/out + hôte validation = preuve insurmontable
   - **Mesure**: Preuve doit être vérifiable par directeur académie en < 2 min sur interface admin
   - **Seuil 90/100**: Preuve lisible, horodatée, GPS + signature hôte

2. ✅ **Fonctionne offline**
   - Check-in/out local sans réseau
   - Sync auto quand réseau revient
   - **Mesure**: Inspecteur peut check-in offline, sync 1h après, visite encore valide
   - **Seuil 90/100**: App offre clear UI "offline mode", pas de perte données

3. ✅ **Pas d'overhead temps**
   - Check-in/out = tap unique, max 5 secondes
   - Aucune saisie supplémentaire (rapport détaillé = V2)
   - **Mesure**: Temps total visite (avec SIGIS) ≈ temps avant (sans)
   - **Seuil 90/100**: Check-in/out ultra-rapide (≤5s, 1-tap)

4. ✅ **Batterie respectée**
   - Géolocalisation = optimisée, pas de drain constant
   - GPS allumé que pendant check-in/out
   - **Mesure**: App = < 2% batterie pour visite 2h (comparé 5%+ Google Maps)
   - **Seuil 90/100**: GPS efficient, pas de background polling

5. ✅ **Transparence données**
   - Charte signée: données = non utilisées contre lui
   - Audit clair: qui voit quoi?
   - **Mesure**: Admin interface montre "logs accès" par inspecteur
   - **Seuil 90/100**: Charte + audit existant, accessible au user

---

### **2. RESPONSABLE D'ACCUEIL** (établissement)

#### **Qui?**
- Directeur école, secrétaire, parent habilité
- Accueille inspecteur, signe "visite"
- Français/anglais/pidgin, peu tech

#### **Vrais problèmes**
| Problème | Contexte | Impact |
|----------|----------|--------|
| **Pas de téléphone compatible** | Vieux téléphone feature-phone ou pas de téléphone | Mode B (QR) doit fonctionner sans app |
| **Pas d'internet** | Zone rurale, zéro réseau | SMS fallback (Mode C) doit être robuste |
| **Doute sur légalité** | "Pourquoi signer électroniquement? C'est légal?" | Besoin preuve légale, pas juste technologique |
| **Utilisation contre lui** | Peur données = rapport négatif = sanction | Confiance = critique |

#### **Attentes objectives**

1. ✅ **Validation en 1-2 taps sans app**
   - **Mode B (QR)**: Scanner QR (même with Google Lens), entrer jeton → valide
   - **Mode C (SMS)**: Recevoir code SMS, taper dans app/web → valide
   - **Mesure**: Hôte sans smartphone peut valider visite < 1 min
   - **Seuil 90/100**: QR works offline (cache) + SMS opérationnel

2. ✅ **Co-présence vérifiable (Time + Distance)**
   - GPS prouve: inspecteur et hôte au même endroit, même moment
   - **Mesure**: Horodatage ± 2 min, distance ≤ 50m
   - **Seuil 90/100**: Temps + distance enregistrés + affichés dans preuve

3. ✅ **Signature preuve (pas falsifiable)**
   - Hôte signature = irréfutable (si device binding solide)
   - **Mesure**: Preuve non modifiable après co-présence validée
   - **Seuil 90/100**: WORM audit + signature device (pas parfait crypto V3, mais sûr)

4. ✅ **Pas de refus arbitraire**
   - Validation = critères clairs (délai, distance, code)
   - Pas "rejet aléatoire" due to bug
   - **Mesure**: Si délai ≤ 15 min + distance ≤ 50m + code juste → ACCEPTÉ
   - **Seuil 90/100**: Règles métier formalisées, pas d'exception ad-hoc

---

### **3. DIRECTEUR ACADÉMIE** (supervision)

#### **Qui?**
- Inspecteur général région/académie
- Supervise 50-200 inspecteurs
- Valide missions, arbitre conflits, produit rapports

#### **Vrais problèmes**
| Problème | Contexte | Impact |
|----------|----------|--------|
| **Vision opérationnelle faible** | Pas de dashboard; rapports papier = retard de 2-3 semaines | Décisions lentes, ciblage impossible |
| **Fraude inspecteur invisible** | Peut pas vérifier si visite = réelle ou fictive | Zéro recours légal contre faux rapports |
| **Missions = chaos** | Planification ad-hoc; doublons; inspecteur "oublie" visite prévue | Couverture irrégulière, zones dé-surveillées |
| **Conflits = non tranchés** | Inspecteur vs directeur école: "visite jamais eu lieu" | Absence arbitrage crédible |

#### **Attentes objectives**

1. ✅ **Dashboard opérationnel en temps réel**
   - Nombre missions par inspecteur / semaine
   - Taux de visite = "avec co-présence validée" vs "sans"
   - Détection anomalies (GPS hors zone, durée < 5 min, etc.)
   - **Mesure**: Admin console montre "Inspecteur X: 8 visites cette semaine, 7 validées"
   - **Seuil 90/100**: Dashboard = mises à jour < 5 min, filtres basiques (par académie, date range, statut)

2. ✅ **Preuve opposable vs disputes**
   - Conflit inspecteur/école = arbitrage facile: "Vous étiez ensemble [timestamp] à [location]"
   - Co-présence GPS = preuve irréfutable (ou SMS code = preuve de réception)
   - **Mesure**: Directeur académie peut trancher dispute < 1 min en regardant preuve
   - **Seuil 90/100**: Preuve = date, heure, GPS (±50m), signataires clairs

3. ✅ **Détection fraude simple**
   - Alerte: inspecteur check-in 5x même lieu même minute (GPS clone)
   - Alerte: inspecteur check-out immédiat (visite < 1 min)
   - Alerte: GPS accuracy très mauvaise (± 200m)
   - **Mesure**: Dashboard = rouge/jaune/vert par anomalie
   - **Seuil 90/100**: Au minimum 5 règles de détection implémentées + auditables

4. ✅ **Rapports mensuels / statistiques**
   - Taux couverture établissements
   - Taux de "visite difficile" (refus accès, incident)
   - Temps moyen visite par région
   - **Mesure**: Export CSV mensuel, sous 1 min
   - **Seuil 90/100**: Reports endpoint REST + CSV/JSON export

---

### **4. JURIDIQUE / CONFORMITÉ** (MINESEC/MINSUB)

#### **Qui?**
- Direction planing/conformité
- Valide respect DPIA, RGPD (si applicable Cameroun)
- Approuve mise en production

#### **Vrais problèmes**
| Problème | Contexte | Impact |
|----------|----------|--------|
| **Données sensibles mal gérées** | GPS enfants (via photos école) = données sensibles | Risque légal + PR catastrophique |
| **Rétention perpétuelle** | Pas de politique suppression = accumulation illimitée | Non-conforme moderne |
| **Audit absent** | "Qui a regardé les données de cet inspecteur?" = pas de trace | Impossible prouver conforme |
| **Consentement flou** | Pas de charte signée par inspecteur/hôte = flou légal | Contrat invalide = procès |

#### **Attentes objectives**

1. ✅ **DPIA complet**
   - Registre traitement (pas dans code, mais document officiel)
   - Évaluation risques (identifiée)
   - Mesures mitigation (charte, audit, retention policy)
   - **Mesure**: Document DPIA signée par direction + experts externes
   - **Seuil 90/100**: DPIA produit, limites identifiées (PostGIS future, RBAC amélioré V2)

2. ✅ **Rétention + suppression**
   - Images: 30–90 jours puis purge (configurable)
   - Métadonnées (GPS, timestamps): 1–2 ans
   - Audit logs: 3 ans
   - **Mesure**: Cron job automatique, logs de suppression
   - **Seuil 90/100**: Policy définie + cron en place, testable

3. ✅ **Audit WORM (Write-Once)**
   - Logs = non modifiables après enregistrement
   - Accès données = tracé (qui, quand, pourquoi)
   - **Mesure**: Requête audit logs = complète, immuable (signature temps)
   - **Seuil 90/100**: Audit stocké DB, append-only, avec IP/user/action/timestamp

4. ✅ **Charte de consentement**
   - Inspecteur signe: "Données non punition, sauf fraude avérée"
   - Hôte signe: "Co-présence GPS = preuve, consenti"
   - **Mesure**: Document PDF + signature electro enregistrée
   - **Seuil 90/100**: Charte intégrée onboarding, signature/timestamp tracée

---

## 📊 **Attentes transversales (tous acteurs)**

### **A. Robustesse réseau (Cameroun reality)**

| Scenario | Exigence |
|----------|----------|
| **Perte réseau 30 min** | App continue fonctionner, sync auto après |
| **Perte réseau 8h** | App queue persiste, reprise sans perte |
| **2G SMS seulement** | Mode C (SMS code) fonctionne 100% |
| **GPS inaccurate** | App accepte ±100m, score comme FAIR, flag en audit |
| **Batterie < 5%** | Check-in/out encore possible, pas d'effet secondaire |

**Mesure**: Cas de test scenario + simulation réseau mauvaise (tc de réseau: latence +5s, perte 10%, jitter)

**Seuil 90/100**: 
- ✅ Offline check-in/out testé
- ✅ Sync queue persiste (JSON local ou IndexedDB)
- ✅ SMS fallback testé (stub ou vrai SMS)
- ✅ GPS degraded mode (fair accuracy accepté)
- ⚠️ Batterie optimization (not blocking, V2+)

---

### **B. Sécurité anti-fraude**

| Vecteur fraude | Mitigation attendue |
|---|---|
| **GPS spoofing** (inspector fake location) | Device binding (public key per phone) + signature (Ed25519) — V2 |
| **Check-in clone** (same location 2x inspectors same minute) | Anomaly alert in dashboard |
| **QR rejeu** | JWT jti consumption (anti-replay) |
| **SMS brute force** | Rate limit SMS generation (max 5/mission) |
| **Hôte usurpation** | Designated host + device binding (V2) |
| **Check-out fabrication** | Séquence d'état stricte (check-in mandatory avant) |

**Mesure**: Chaque vecteur = testable dans scenario E2E

**Seuil 90/100**:
- ✅ Device binding implémenté (V2 avec public key)
- ✅ Anomaly detection (5 règles min: clone, too-short, bad GPS, etc.)
- ✅ JWT jti anti-replay
- ✅ Séquence d'état stricte

---

### **C. Adoptabilité**

| Aspect | Exigence |
|---|---|
| **Temps apprentissage** | Inspecteur learn in < 10 min sans formation |
| **Clics pour visite** | ≤ 5 taps total (check-in 2, host validation 2, check-out 1) |
| **Messages d'erreur** | En français clair, pas codes techniques |
| **Non-blockers** | Si SIGIS fail, inspecteur peut continuer (fallback papier) |
| **Trust building** | Dès semaine 1, inspecteur voit: "mon visite est preuve" |

**Mesure**: Usability test avec 5-10 inspecteurs réels + feedback

**Seuil 90/100**:
- ✅ UX flow < 15s par action (check-in/out, host validate)
- ✅ Erreurs françaises (ou multilingue)
- ✅ Offline graceful degradation
- ✅ Success feedback instant ("Co-présence validée ✅")

---

### **D. Observabilité production**

| Besoin | Implémentation |
|---|---|
| **Incident détection** | Alertes: API latency > 2s, error rate > 1%, offline queue size > 100 |
| **Debugging** | Request ID + correlation logs |
| **Capacity planning** | APM: peak hours, avg response times, DB queries slow |
| **SLA tracking** | Uptime %, recovery time, data consistency checks |

**Mesure**: Monitoring stack en place (Prometheus ou CloudWatch)

**Seuil 90/100**:
- ✅ Request ID tracing
- ✅ Error rate tracking
- ✅ API latency SLA (p95 < 2s)
- ✅ Data consistency validation

---

## 🎯 **Attentes par étape (V1 → V2 → V3)**

### **V1 (MAINTENANT)**
Les inspecteurs/hôtes peuvent:
- ✅ Check-in inspecteur avec GPS
- ✅ Valider co-présence (A/B/C modes)
- ✅ Check-out → durée calculée
- ✅ Voir preuve basique (heure, lieu, noms)
- ✅ Admin voit dashboard simple (count, status)

**Mesure succès V1**: 80% inspecteurs actifs après 3 mois, 0 data loss, zéro fraude détectée (baseline)

---

### **V2 (6-12 mois après V1)**
- ✅ Offline-first mobile (React Native)
- ✅ Sync batch + delta
- ✅ Device binding (public key Ed25519)
- ✅ Rapport détaillé (MissionOutcome riche)
- ✅ PostGIS pour géofence
- ✅ Anomaly detection advanced (5+ rules)
- ✅ SMS intégration opérateur réelle

**Mesure succès V2**: 90% inspecteurs, 50% visites = offline-first, detectable fraude patterns

---

### **V3 (18+ mois après V1)**
- ✅ WORM audit immuable (blockchain-style)
- ✅ Signature cryptographique complète
- ✅ Rapport PDF auto-généré certifié
- ✅ IntégrORM système académie existant
- ✅ RBAC fine-grained, audit rows-level

**Mesure succès V3**: Preuve = légalement opposable en cour

---

## 📋 **Checklist: 90/100 attentes métier (V1)**

```
INSPECTEUR
☐ Check-in/out offline possible
☐ Co-présence en < 30s
☐ Preuve horodatée + GPS + signataire
☐ Messages d'erreur français clairs
☐ Pas d'overhead temps vs avant
☐ Battery friendly (géo optimisé)

RESPONSABLE ACCUEIL
☐ Mode B (QR) sans app smartphone
☐ Mode C (SMS) operationnel
☐ Co-présence temps + distance enregistrée
☐ Signature non-falsifiable
☐ Règles métier formalisées (délai/distance)

DIRECTEUR ACADÉMIE
☐ Dashboard: count missions, taux validation
☐ Anomaly alerts (5+ rules min)
☐ Arbitrage facile (timestamp + GPS proof)
☐ Export CSV rapide
☐ Audit accessible (qui a vu quoi)

CONFORMITÉ
☐ DPIA document signé
☐ Rétention policy (30-90j images, 1-2y métadonnées)
☐ Audit WORM (non-modifiable)
☐ Charte consentement intégrée
☐ Limites documentées (PostGIS, V3 crypto)

TRANSVERSAL
☐ Offline 30min+ supported
☐ GPS ≤100m accepted, scored
☐ Device binding (V2, but track now)
☐ JTI anti-replay QR
☐ Request ID tracing
☐ Error rate < 1%, latency p95 < 2s
☐ UX < 15s per action
☐ Non-blocking fallback (paper)
```

---

## 🏆 **Score 90/100 = ?**

**V1 MVP hits 90/100 when**:

1. **Métier** (40 points)
   - ✅ Check-in/out cycle complete (10)
   - ✅ Co-présence 3 modes A/B/C (10)
   - ✅ Preuve horodatée + GPS (10)
   - ✅ Offline grace timestamps (10)

2. **Sécurité minimum** (20 points)
   - ✅ Device binding v1 (5)
   - ✅ JTI anti-replay (5)
   - ✅ Anomaly detection 5+ rules (5)
   - ✅ Audit logs WORM (5)

3. **Conformité** (15 points)
   - ✅ DPIA signed (5)
   - ✅ Rétention policy (5)
   - ✅ Charte consentement (5)

4. **UX/Adoptabilité** (15 points)
   - ✅ < 15s flow (5)
   - ✅ Offline working (5)
   - ✅ French clear errors (5)

**Score < 90/100** si manquent:
- ❌ Offline grace timestamps (coeur métier V1)
- ❌ Device binding (traçabilité)
- ❌ Anomaly detection (no fraud alert)
- ❌ DPIA/charte (compliance risk)
- ❌ UX tested (adoption fail)

---

*Mis à jour: 2026-07-14 — Alignement MINESEC/MINSUB, contexte terrain Cameroun*
