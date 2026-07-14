# Release Process — SIGIS V1

Versioning automatique basé sur **Conventional Commits** avec **Semantic Versioning**.

---

## 📌 Versioning Scheme

Trois chiffres: **MAJOR.MINOR.PATCH**

### Mapping Commits → Versions

| Type de commit | Version | Exemple |
|---|---|---|
| `feat:` | Minor | 0.1.0 → 0.2.0 |
| `fix:`, `perf:` | Patch | 0.2.0 → 0.2.1 |
| `BREAKING CHANGE` ou `type!:` | Major | 0.2.1 → 1.0.0 |
| `docs`, `chore`, `style`, `test`, `refactor` | Pas de release | (no bump) |

---

## 🏗️ Release Workflow

### Prerequisites

```bash
# Vérifier qu'on est sur main et à jour
git checkout main
git pull origin main

# Vérifier que CI est verte
# (tous les checks GitHub Actions passent)
```

### Step 1: Create Release Branch

```bash
# Créer branche release (ex: v0.2.0)
git checkout -b release/v0.2.0

# Mettre à jour version dans pyproject.toml
# Avant:  version = "0.1.0"
# Après:  version = "0.2.0"
```

### Step 2: Update Changelog

```markdown
## [0.2.0] - 2026-07-14

### Added
- feat(auth): add refresh token rotation
- feat(api): add /anomalies endpoint

### Fixed
- fix(db): handle concurrent migrations

### Changed
- perf(geofence): optimize haversine calculation
```

### Step 3: Create Release Commit

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): version 0.2.0"
git push origin release/v0.2.0
```

### Step 4: Create Release PR

```bash
gh pr create \
  --title "chore(release): v0.2.0" \
  --body "Release version 0.2.0 with X features, Y fixes"
```

### Step 5: Merge & Tag

```bash
# Merge PR (squash merge)
gh pr merge --squash --auto

# Tag the release
git tag v0.2.0 main
git push origin v0.2.0

# GitHub automatically creates Release notes from tag
```

---

## 📦 Version History

### Current Version
**v0.1.0** (2026-07-14)
- Initial V1 release
- Offline grace timestamps
- GPS accuracy scoring
- Device binding v1
- 5+ anomaly detection rules
- 69 domain tests (100% pass)
- 90%+ coverage target

### Planned (V1 production)
**v0.2.0** (est. 2026-08-14)
- UC integration (check-in, confirm-host, checkout)
- ORM migrations (accuracy_m, gps_score, device_id)
- API endpoints (/anomalies, device management)
- Load testing & optimization

### Planned (V2+)
**v1.0.0** (est. 2026-10-14)
- Mobile app (React Native) offline-first
- PostGIS for geofence scalability
- Real SMS integration
- WORM audit immuable
- Ed25519 signature crypto

---

## 🔔 Release Notifications

Après merge du release PR:

1. **GitHub Releases** — Auto-generated notes
2. **Slack** — Notification to #releases channel
3. **MINESEC** — Email summary (manual, for now)

Template:
```
🎉 SIGIS v0.2.0 released!

🚀 Features
- UC integration complete
- API endpoints live
- Load tested (1000+ missions/day)

🐛 Fixes
- Performance optimization
- Database consistency fixes

📊 Metrics
- 69 tests (100% pass)
- 90%+ coverage
- < 500ms p95 latency

Changelog: https://github.com/nb-bora/sigis-backend/releases/tag/v0.2.0
```

---

## 🛠️ Hotfix Process

If critical bug found in production:

```bash
# Create hotfix branch from tag
git checkout -b hotfix/v0.2.1 v0.2.0

# Fix the issue
# Commit with: fix(domain): critical bug fix
git commit -m "fix(domain): fix mission window validation bug"

# Create release with same process
# Version bumps: 0.2.0 → 0.2.1 (Patch)
```

---

## 📋 Release Checklist

- [ ] All commits follow Conventional Commits
- [ ] CI pipeline is green
- [ ] Coverage ≥ 90%
- [ ] Version bumped in `pyproject.toml`
- [ ] `CHANGELOG.md` updated
- [ ] Release PR created & approved
- [ ] Release PR merged to main
- [ ] Git tag created (v0.2.0)
- [ ] Release notes published
- [ ] Stakeholders notified

---

## 🚀 Deployment Timeline

| Version | Target Date | Status | Focus |
|---------|---|---|---|
| v0.1.0 | 2026-07-14 | ✅ DONE | Foundation (domain + tests) |
| v0.2.0 | 2026-08-14 | ⏳ In Progress | UC integration + API |
| v0.3.0 | 2026-09-14 | 📋 Planned | Load testing + prod hardening |
| v1.0.0 | 2026-10-14 | 🎯 Target | Mobile app + crypto |

---

## 📞 Contact

Release questions → @brice-devops237 (MINESEC project lead)

---

*Last updated: 2026-07-14*  
*Process version: 1.0*
