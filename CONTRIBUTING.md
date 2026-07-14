# Contribution Guidelines — SIGIS Backend

Bienvenue! Merci de contribuer à SIGIS. Voici les règles de contribution pour assurer un historique Git propre et une meilleure qualité de code.

---

## 🎯 Règles Pull Requests

### Création de la PR
- ✅ Créer la branche à partir de **`main`**
- ✅ Ouvrir une PR vers **`main`**
- ✅ ❌ Aucun push direct sur `main`

### Titre & Description obligatoires

**Titre**: Respecter **Conventional Commits** (voir section ci-dessous)

**Description** doit contenir:
- **Ce qui change** (quoi)
- **Pourquoi** (motivation)
- **Comment tester** (test plan)
- **Ticket associé** (lien)

Exemple:
```
feat(auth): add refresh token rotation

## Summary
- Adds automatic token refresh every 24h
- Invalidates old tokens via blacklist
- Stores rotation history in audit logs

## Test plan
- [ ] Login flow still works
- [ ] Token refresh happens silently
- [ ] Old tokens rejected after rotation
- [ ] Audit logs show rotation events

Closes #123
```

### Approbations & Merge

- ✅ CI pipeline doit être verte
- ✅ Tous les review comments résolus
- ✅ Au moins **1 approbation** requise
- ✅ Taille recommandée: **< 400 lignes** (ou justifier)

---

## 📝 Conventional Commits

### Format obligatoire

```
type(scope): description
```

### Types acceptés

| Type | Version | Description |
|------|---------|-------------|
| `feat` | Minor | Nouvelle fonctionnalité |
| `fix` | Patch | Correction de bug |
| `perf` | Patch | Optimisation performance |
| `docs` | - | Documentation |
| `style` | - | Formatage/style (no logic change) |
| `refactor` | - | Refactoring (no behavior change) |
| `test` | - | Tests seulement |
| `chore` | - | Dépendances, build, CI/CD |

### Scopes acceptés

Utiliser le contexte pertinent:
- `(auth)` — Authentification/autorisation
- `(api)` — Endpoints REST
- `(db)` — Persistance/migrations
- `(domain)` — Règles métier
- `(test)` — Tests/fixtures
- `(ci)` — Pipeline/workflows
- `(docs)` — Documentation
- Ou custom selon domaine

### Exemples valides

```bash
feat(auth): add refresh token rotation
fix(api): handle timeout on Amadeus integration
perf(db): add index on mission queries
docs(readme): update setup instructions
chore(ci): upgrade Python to 3.12
feat!: remove legacy webhook payload (BREAKING)
```

### Exemples INVALIDES ❌

```bash
update          # Trop vague
fix bug         # Pas de type/scope
WIP             # Non descriptif
Update auth     # Minuscule après type
```

---

## 🏗️ Processus de Merge

1. **Title check** ✅ Conventional Commits
2. **Lint** ✅ Ruff check + format
3. **Tests** ✅ 90% coverage minimum
4. **Review** ✅ Approbation requise
5. **Merge** ✅ Squash merge (utilise le titre de PR)

Le titre de PR devient le commit final → **doit respecter Conventional Commits**.

---

## 📋 Checklist avant push

```bash
# 1. Lancer ruff check
ruff check .

# 2. Formater le code
ruff format .

# 3. Lancer les tests (90% coverage min)
pytest --cov=domain,application,infrastructure,api,common --cov-fail-under=90

# 4. Vérifier titre PR (Conventional Commits)
# Titre: feat(domain): add offline grace timestamps

# 5. Rédiger description (quoi/pourquoi/comment/ticket)
```

---

## 🚀 Versioning Automatique

En fonction des commits, la version est auto-incrémentée:

- `feat:` → **Minor** (0.x.0)
- `fix:`, `perf:` → **Patch** (0.0.x)
- `feat!:` ou `BREAKING CHANGE:` → **Major** (1.0.0)
- Autres types → **Pas de release**

---

## 🔍 CI Pipeline

La pipeline vérifie:

✅ **Conventional Commits** (PR title)  
✅ **Ruff lint** (`ruff check .`)  
✅ **Ruff format** (`ruff format --check .`)  
✅ **Tests** (pytest)  
✅ **Coverage ≥ 90%** (fail-under=90)  
✅ **Migrations** (alembic upgrade head)  

Tous les checks doivent être verts avant merge.

---

## 📚 Ressources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [SIGIS Architecture](./docs/ARCHITECTURE.md)
- [Testing Guide](./TESTING.md)
- [CLAUDE.md](./CLAUDE.md) — Contexte projet

---

Merci de respecter ces règles pour maintenir une qualité élevée! 🙏

