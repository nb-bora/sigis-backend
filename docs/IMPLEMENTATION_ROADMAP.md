# Roadmap implémentation détaillée — 62 → 90/100

**Durée totale**: 13 jours (3 semaines)  
**Ordre**: Critiques → Conformité → Polish

---

## **PHASE 1 — CRITIQUES MÉTIER (10 jours)**

### **Sprint 1A — Offline grace timestamps (3 jours)**

**Objectif**: Accepter timestamps client, vérifier fenêtre avec client time (pas serveur).

#### **Jour 1: Préparation schema + UC**

**1.1 — Étendre schémas Pydantic** (`api/v1/schemas.py`)
```python
# Ajouter captured_at_client à tous les DTO
@dataclass
class CheckInRequest:
    mission_id: UUID
    latitude: float
    longitude: float
    client_request_id: str
    host_validation_mode: str
    captured_at_client: datetime  # ← NEW (ISO8601)
    accuracy_m: float | None = None  # ← NEW (GPS quality)

@dataclass
class ConfirmHostRequest:
    site_visit_id: UUID
    mission_id: UUID
    client_request_id: str
    latitude: float | None = None
    longitude: float | None = None
    qr_token: UUID | None = None
    qr_jwt: str | None = None
    sms_code: str | None = None
    captured_at_client: datetime  # ← NEW
    accuracy_m: float | None = None  # ← NEW

@dataclass
class CheckOutRequest:
    site_visit_id: UUID
    client_request_id: str
    captured_at_client: datetime  # ← NEW
```

**1.2 — Créer règle métier client timestamps** (`domain/shared/client_time_validation.py` — NEW FILE)
```python
"""Validation fenêtre mission utilisant timestamps client."""

from datetime import UTC, datetime
from domain.errors import DomainError

def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

def ensure_mission_window_client_time(
    captured_at_client: datetime,
    window_start: datetime,
    window_end: datetime,
) -> None:
    """Vérifier que timestamp CLIENT est dans fenêtre mission.
    
    Permet offline: visite faite offline à 14h, sync à 18h = OK si 14h ∈ [14h, 16h].
    """
    ct = _aware(captured_at_client)
    ws = _aware(window_start)
    we = _aware(window_end)
    
    if not (ws <= ct <= we):
        raise DomainError(
            "Événement hors fenêtre mission.",
            code="MISSION_EXPIRED_CLIENT_TIME"
        )
```

**Files to modify**:
- `api/v1/schemas.py` ← add captured_at_client to all request DTOs
- `domain/shared/client_time_validation.py` ← CREATE
- `domain/shared/__init__.py` ← export new function

---

#### **Jour 2: Modifier UC check-in/confirm/checkout**

**2.1 — CheckInInspector** (`application/use_cases/check_in_inspector.py`)
```python
# OLD:
ensure_mission_window(now, mission.window_start, mission.window_end)

# NEW:
from domain.shared.client_time_validation import ensure_mission_window_client_time
ensure_mission_window_client_time(
    cmd.captured_at_client,  # ← use client time
    mission.window_start,
    mission.window_end
)
```

**2.2 — ConfirmHostPresence** (`application/use_cases/confirm_host_presence.py`)
```python
# OLD:
# no explicit window check for confirm_host

# NEW: Add explicit check
ensure_mission_window_client_time(
    cmd.captured_at_client,
    mission.window_start,
    mission.window_end
)
```

**2.3 — CheckOutVisit** (`application/use_cases/check_out_visit.py`)
```python
# OLD:
check_out(visit, now=datetime.now(UTC))

# NEW:
from domain.shared.client_time_validation import ensure_mission_window_client_time

async def execute(self, cmd: CheckOutCommand) -> dict:
    # ... validate visit exists ...
    
    # Verify client time still within window
    ensure_mission_window_client_time(
        cmd.captured_at_client,
        mission.window_start,
        mission.window_end
    )
    
    check_out(visit, now=cmd.captured_at_client)  # Use client time
    await self._uow.site_visits.update(visit)
    return {...}
```

**2.4 — Update transitions.py to accept client time**
```python
# OLD:
def check_out(visit: SiteVisit, *, now: datetime) -> None:
    visit.checked_out_at = now.astimezone(UTC) ...

# STAY SAME (now = checked_out_at en local client time)
```

**Files to modify**:
- `application/use_cases/check_in_inspector.py` ← use client time
- `application/use_cases/confirm_host_presence.py` ← add window check
- `application/use_cases/check_out_visit.py` ← new UC or extend existing

---

#### **Jour 3: Tests + validation**

**3.1 — Tests offline grace scenario**
```python
# tests/test_offline_grace.py (NEW FILE)
@pytest.mark.asyncio
async def test_checkin_offline_sync_later():
    """Inspecteur check-in offline à 14h, sync à 18h → OK si 14h ∈ fenêtre."""
    mission = create_mission(window_start=14h, window_end=16h)
    
    # Simulate offline: captured_at_client = 14h30
    cmd = CheckInInspectorCommand(
        mission_id=mission.id,
        inspector_user_id=...,
        latitude=..., longitude=...,
        client_request_id="offline-1",
        captured_at_client=datetime(14, 30),  # ← offline time
        accuracy_m=10.0
    )
    
    # Execute at 18h server time
    result = await uc.execute(cmd)
    
    # Should succeed (client time 14h30 ∈ [14h, 16h])
    assert result["status"] == "CHECKED_IN"
```

**Files to create**:
- `tests/test_offline_grace.py` ← test suite

**Deliverable after Day 3**:
- ✅ Client timestamps collected and validated
- ✅ Offline scenarios passing
- **Score gained**: +5/100 (vers 67/100)

---

### **Sprint 1B — GPS accuracy scoring (2 jours)**

**Objectif**: Collecter accuracy_m, scorer qualité GPS, flaguer anomalies.

#### **Jour 4: Règles métier GPS**

**4.1 — Créer module GPS quality** (`domain/shared/gps_quality.py` — NEW FILE)
```python
"""Scoring qualité GPS pour détection fraude."""

from enum import StrEnum
from dataclasses import dataclass

class GpsScore(StrEnum):
    EXCELLENT = "excellent"  # ≤ 5m
    GOOD = "good"              # 5–25m
    FAIR = "fair"              # 25–100m
    POOR = "poor"              # > 100m

@dataclass(frozen=True)
class GpsQuality:
    accuracy_m: float
    provider: str  # "gps" | "network" | "fused" | "cached"
    hdop: float | None = None

def score_gps_accuracy(accuracy_m: float) -> GpsScore:
    """Score la qualité GPS."""
    if accuracy_m <= 5:
        return GpsScore.EXCELLENT
    elif accuracy_m <= 25:
        return GpsScore.GOOD
    elif accuracy_m <= 100:
        return GpsScore.FAIR
    else:
        return GpsScore.POOR
```

**4.2 — Étendre ORM models** (`infrastructure/persistence/sqlalchemy/models.py`)
```python
# Update PresenceProof ORM
class PresenceProofORM(Base):
    __tablename__ = "presence_proofs"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    site_visit_id: Mapped[UUID] = mapped_column(ForeignKey("site_visits.id"))
    actor_user_id: Mapped[UUID]
    latitude: Mapped[float]
    longitude: Mapped[float]
    geofence_status: Mapped[str]
    
    # NEW:
    accuracy_m: Mapped[float | None] = mapped_column(nullable=True)
    gps_provider: Mapped[str | None] = mapped_column(nullable=True)
    gps_score: Mapped[str] = mapped_column(default="FAIR")  # EXCELLENT/GOOD/FAIR/POOR
    
    created_at: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)
```

**4.3 — Modifier domain model** (`domain/presence/models.py`)
```python
@dataclass
class PresenceProof:
    id: UUID
    site_visit_id: UUID
    actor_user_id: UUID
    latitude: float
    longitude: float
    geofence_status: str
    
    # NEW:
    accuracy_m: float | None = None
    gps_provider: str | None = None
    gps_score: str = "FAIR"  # default
    
    recorded_at: datetime | None = None
```

**Files to create/modify**:
- `domain/shared/gps_quality.py` ← CREATE
- `infrastructure/persistence/sqlalchemy/models.py` ← add accuracy_m, gps_score
- `domain/presence/models.py` ← add fields
- `domain/presence/__init__.py` ← export GpsScore

---

#### **Jour 5: UC + tests GPS**

**5.1 — CheckInInspector: calculer GPS score**
```python
# application/use_cases/check_in_inspector.py
from domain.shared.gps_quality import score_gps_accuracy

async def execute(self, cmd: CheckInInspectorCommand) -> dict:
    # ... existing logic ...
    
    # NEW: Score GPS quality
    gps_score = score_gps_accuracy(cmd.accuracy_m or 50.0)  # default 50m if absent
    
    proof = PresenceProof(
        id=uuid4(),
        site_visit_id=visit.id,
        actor_user_id=cmd.inspector_user_id,
        recorded_at=now,
        latitude=cmd.latitude,
        longitude=cmd.longitude,
        geofence_status=gf,
        accuracy_m=cmd.accuracy_m,
        gps_provider=cmd.gps_provider,
        gps_score=gps_score.value,
    )
    await self._uow.presence_proofs.add(proof)
```

**5.2 — Idem pour ConfirmHostPresence**
```python
# application/use_cases/confirm_host_presence.py
if mode == HostValidationMode.APP_GPS:
    gps_score = score_gps_accuracy(cmd.accuracy_m or 50.0)
    
    event = CoPresenceEvent(
        id=uuid4(),
        site_visit_id=cmd.site_visit_id,
        actor_user_id=cmd.host_user_id,
        validated_at=now,
        latitude=cmd.latitude,
        longitude=cmd.longitude,
        gps_score=gps_score.value,  # ← track quality
        accuracy_m=cmd.accuracy_m,
    )
```

**5.3 — Tests**
```python
# tests/test_gps_scoring.py (NEW FILE)
def test_gps_score_excellent():
    assert score_gps_accuracy(3.0) == GpsScore.EXCELLENT

def test_gps_score_poor():
    assert score_gps_accuracy(150.0) == GpsScore.POOR

@pytest.mark.asyncio
async def test_checkin_captures_gps_quality():
    """Check-in doit capturer et scorer accuracy_m."""
    result = await uc.execute(CheckInInspectorCommand(
        ...,
        accuracy_m=25.0  # GOOD
    ))
    
    proof = await uow.presence_proofs.get_by_id(...)
    assert proof.gps_score == "GOOD"
    assert proof.accuracy_m == 25.0
```

**Files to create/modify**:
- `application/use_cases/check_in_inspector.py` ← add GPS scoring
- `application/use_cases/confirm_host_presence.py` ← add GPS scoring
- `tests/test_gps_scoring.py` ← CREATE
- DB migration: add columns

**Deliverable after Day 5**:
- ✅ GPS accuracy_m collected
- ✅ GPS score (EXCELLENT/GOOD/FAIR/POOR) assigned
- **Score gained**: +6/100 (vers 73/100)

---

### **Sprint 1C — Device binding v1 (2 jours)**

**Objectif**: Tracker device_id + public_key, reject si key changes.

#### **Jour 6: Schema + UC**

**6.1 — Créer domain model** (`domain/identity/device.py` — NEW FILE)
```python
"""Device binding — une app/device = une clé publique."""

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

@dataclass
class MobileDevice:
    id: UUID
    user_id: UUID
    device_id: str  # UUID from mobile app
    public_key_ed25519: str  # hex-encoded public key
    device_name: str | None = None  # "iPhone 12", "Tecno Spark", etc.
    first_seen_at: datetime
    last_seen_at: datetime
```

**6.2 — Étendre ORM** (`infrastructure/persistence/sqlalchemy/models.py`)
```python
class MobileDeviceORM(Base):
    __tablename__ = "mobile_devices"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    device_id: Mapped[str] = mapped_column(unique=True, index=True)  # unique per device
    public_key_ed25519: Mapped[str]
    device_name: Mapped[str | None]
    first_seen_at: Mapped[datetime]
    last_seen_at: Mapped[datetime]
```

**6.3 — Repo + UoW** (`infrastructure/persistence/sqlalchemy/device_repo.py` — NEW FILE)
```python
class MobileDeviceRepository:
    async def get_or_create(
        self,
        user_id: UUID,
        device_id: str,
        public_key: str,
        device_name: str | None = None,
    ) -> MobileDevice:
        """Get device if exists, or create new if key matches."""
        existing = await self.session.execute(
            select(MobileDeviceORM)
            .where(MobileDeviceORM.device_id == device_id)
        )
        orm = existing.scalar_one_or_none()
        
        if orm is None:
            # First time seeing this device
            orm = MobileDeviceORM(
                id=uuid4(),
                user_id=user_id,
                device_id=device_id,
                public_key_ed25519=public_key,
                device_name=device_name,
                first_seen_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
            )
            self.session.add(orm)
        else:
            # Device seen before — verify key matches
            if orm.public_key_ed25519 != public_key:
                raise Forbidden(
                    "Device ID exists but public key mismatch (possible compromise).",
                    code="DEVICE_KEY_MISMATCH"
                )
            orm.last_seen_at = datetime.now(UTC)
        
        return self._map_to_domain(orm)
```

**6.4 — Modifier CheckInInspector UC**
```python
# application/use_cases/check_in_inspector.py
@dataclass(frozen=True)
class CheckInInspectorCommand:
    # ... existing ...
    device_id: str  # ← NEW: UUID from mobile
    device_public_key: str  # ← NEW: ED25519 hex

async def execute(self, cmd: CheckInInspectorCommand) -> dict:
    # Track device
    device = await self._uow.mobile_devices.get_or_create(
        user_id=cmd.inspector_user_id,
        device_id=cmd.device_id,
        public_key=cmd.device_public_key,
    )
    
    # Rest of logic...
    proof = PresenceProof(
        id=uuid4(),
        ...,
        device_id=device.id,  # ← link proof to device
    )
```

**Files to create/modify**:
- `domain/identity/device.py` ← CREATE
- `infrastructure/persistence/sqlalchemy/models.py` ← add MobileDeviceORM
- `infrastructure/persistence/sqlalchemy/device_repo.py` ← CREATE
- `application/use_cases/check_in_inspector.py` ← add device tracking
- DB migration

**Deliverable after Day 6**:
- ✅ Device binding tracked
- ✅ Key mismatch detection
- **Score gained**: +4/100 (vers 77/100)

---

### **Sprint 1D — Anomaly detection rules (2 jours)**

**Objectif**: 5+ règles pour détecter fraude.

#### **Jour 7: Règles métier anomalies**

**7.1 — Créer module anomaly** (`domain/shared/anomaly_detection.py` — NEW FILE)
```python
"""Anomaly detection rules — 5+ pour détection fraude."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

class AnomalyType(StrEnum):
    GPS_CLONE = "gps_clone"          # Same inspector, same location, same minute
    VISIT_TOO_SHORT = "visit_too_short"  # Duration < 5 min
    GPS_POOR_QUALITY = "gps_poor"    # accuracy > 100m
    QR_REJEU = "qr_rejeu"            # Same QR used twice (JTI check)
    RAPID_MULTIPLE = "rapid_multiple"  # Check-in/out 3x in 1 hour (suspicious)

@dataclass(frozen=True)
class Anomaly:
    type: AnomalyType
    severity: str  # "low", "medium", "high"
    description: str
    entity_id: UUID  # presence_proof or site_visit
    detected_at: datetime

# Rule functions (détaillées en code vrai)
async def detect_gps_clone(
    uow: UnitOfWork,
    inspector_id: UUID,
    latitude: float,
    longitude: float,
    check_in_at: datetime,
) -> list[Anomaly]:
    """Détecter si inspecteur a check-in au même lieu dans même minute."""
    # Query: same inspector, ≤50m, ≤1 minute
    # Return list of anomalies if > 1 match

async def detect_visit_too_short(
    checked_in_at: datetime,
    checked_out_at: datetime,
) -> list[Anomaly]:
    """Visite < 5 min = anomaly."""
    duration = checked_out_at - checked_in_at
    if duration < timedelta(minutes=5):
        return [Anomaly(
            type=AnomalyType.VISIT_TOO_SHORT,
            severity="low",
            description=f"Visite {duration.total_seconds()/60:.1f} min < 5 min min",
            ...
        )]
```

#### **Jour 8: Dashboard endpoint + tests**

**8.1 — API endpoint anomalies** (`api/v1/anomalies.py` — NEW FILE)
```python
@router.get("/anomalies")
async def get_anomalies(
    skip: int = 0,
    limit: int = 100,
    severity: str | None = None,
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List anomalies detected."""
    anomalies = await uow.anomalies.list_all(
        skip=skip,
        limit=limit,
        severity_filter=severity,
    )
    return {"anomalies": [a.model_dump() for a in anomalies]}
```

**8.2 — Tests détection**
```python
# tests/test_anomaly_detection.py (NEW FILE)
@pytest.mark.asyncio
async def test_detect_visit_too_short():
    """Visite 2 min should trigger anomaly."""
    anomalies = detect_visit_too_short(
        checked_in_at=datetime(14, 0),
        checked_out_at=datetime(14, 2),
    )
    assert len(anomalies) == 1
    assert anomalies[0].type == AnomalyType.VISIT_TOO_SHORT
```

**Files to create/modify**:
- `domain/shared/anomaly_detection.py` ← CREATE (5+ rules)
- `api/v1/anomalies.py` ← CREATE
- `tests/test_anomaly_detection.py` ← CREATE

**Deliverable after Day 8**:
- ✅ 5+ anomaly rules implemented
- ✅ Dashboard endpoint
- **Score gained**: +8/100 (vers 85/100)

---

**Phase 1 Total: +22 points → 85/100**

---

## **PHASE 2 — CONFORMITÉ (5 jours)**

### **Sprint 2A — DPIA + Audit (2 jours)**

#### **Jour 9: DPIA document + audit immuabilité**

**9.1 — Rédiger DPIA** (documentation/DPIA_SIGIS_V1.md — NEW FILE)
- Traitement données (qui, quoi, pourquoi)
- Risques identifiés (GPS enfants, rétention, accès)
- Mesures mitigation (charte, audit, rétention cron)
- Limites V1 (pas WORM complet, pas crypto V3)

**9.2 — Tester audit immuabilité**
```python
# tests/test_audit_immutability.py (NEW FILE)
@pytest.mark.asyncio
async def test_audit_log_nonmodifiable():
    """Audit logs cannot be deleted/updated."""
    log = await uow.audit_logs.get_by_id(log_id)
    
    # Try to update
    with pytest.raises(Forbidden):
        log.action = "modified"
        await uow.audit_logs.update(log)
```

**Files to create**:
- `docs/DPIA_SIGIS_V1.md` ← CREATE
- `tests/test_audit_immutability.py` ← CREATE

---

#### **Jour 10: Rétention cron + charte**

**10.1 — Rétention images** (`scripts/retention_cleanup.py` — NEW FILE)
```python
#!/usr/bin/env python3
"""Cleanup images older than 90 days."""

import asyncio
from datetime import datetime, timedelta, UTC
from infrastructure.persistence.sqlalchemy.session import create_engine

async def main():
    # Get all media files > 90 days old
    cutoff = datetime.now(UTC) - timedelta(days=90)
    media_to_delete = await session.execute(
        select(MediaORM).where(MediaORM.created_at < cutoff)
    )
    
    for media in media_to_delete:
        # Delete from storage
        delete_from_s3(media.s3_path)
        # Delete record
        await session.delete(media)
    
    await session.commit()
    print(f"Deleted {len(media_to_delete)} old media files")

# Schedule as cron: 0 2 * * * (daily at 2am)
```

**10.2 — Charte intégrée** (`api/v1/onboarding.py` — NEW FILE)
```python
@router.post("/onboarding/accept-charter")
async def accept_charter(
    user_id: UUID = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Enregistrer acceptation charte par utilisateur."""
    user = await uow.users.get_by_id(user_id)
    user.charter_accepted_at = datetime.now(UTC)
    await uow.users.update(user)
    return {"status": "charter_accepted"}
```

**Files to create**:
- `scripts/retention_cleanup.py` ← CREATE
- `api/v1/onboarding.py` ← CREATE
- `docs/CHARTER_SIGIS.md` ← reference (signée hors code)

**Phase 2 Total: +9 points → 94/100** ✅

---

## **PHASE 3 — POLISH (3 jours)**

### **Sprint 3A — Observabilité (1 jour)**

**Jour 11: APM + Monitoring**

**11.1 — Prometheus metrics** (`infrastructure/monitoring.py` — NEW FILE)
```python
from prometheus_client import Counter, Histogram, Gauge

# Latency
api_latency = Histogram(
    'api_latency_seconds',
    'API request latency',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Errors
api_errors = Counter(
    'api_errors_total',
    'API errors',
    ['method', 'endpoint', 'status']
)

# SLA: p95 < 2s
sla_violation = Counter(
    'sla_violations',
    'Latency SLA violations',
    ['endpoint']
)
```

**Files to create**:
- `infrastructure/monitoring.py` ← CREATE
- `docker-compose.override.yml` ← add Prometheus

---

### **Sprint 3B — Durée + grace period (1 jour)**

**Jour 12: Minimum duration + mission grace**

**12.1 — Check-out validation** (`domain/site_visit/transitions.py`)
```python
MINIMUM_VISIT_DURATION_MINUTES = 5

def check_out(visit: SiteVisit, *, now: datetime) -> None:
    if visit.checked_in_at is None:
        raise InvariantViolation("Check-out sans check-in.")
    
    duration = now - visit.checked_in_at
    if duration < timedelta(minutes=MINIMUM_VISIT_DURATION_MINUTES):
        raise InvariantViolation(
            f"Durée minimum: {MINIMUM_VISIT_DURATION_MINUTES} min."
        )
    
    visit.checked_out_at = now
    visit.status = SiteVisitStatus.COMPLETED
```

**12.2 — Grace period mission** (`domain/shared/client_time_validation.py`)
```python
MISSION_GRACE_BEFORE_MINUTES = 10
MISSION_GRACE_AFTER_MINUTES = 15

def ensure_mission_window_with_grace(
    captured_at_client: datetime,
    window_start: datetime,
    window_end: datetime,
) -> None:
    """Vérifier avec tolérance (±10 avant, ±15 après)."""
    effective_start = window_start - timedelta(minutes=MISSION_GRACE_BEFORE_MINUTES)
    effective_end = window_end + timedelta(minutes=MISSION_GRACE_AFTER_MINUTES)
    
    ct = _aware(captured_at_client)
    if not (effective_start <= ct <= effective_end):
        raise DomainError("Hors fenêtre mission (grace incl).")
```

---

### **Sprint 3C — Usability test (1 jour)**

**Jour 13: Simulation/test réel**

**13.1 — Test scenario E2E complet**
```python
# tests/test_e2e_full_flow.py (EXTEND)
@pytest.mark.asyncio
async def test_complete_visit_flow():
    """Inspecteur check-in → hôte valide → check-out (offline simulation)."""
    
    # 1. Check-in offline at 14:00
    checkin_result = await checkin_uc.execute(CheckInInspectorCommand(
        mission_id=mission.id,
        inspector_user_id=inspector.id,
        latitude=..., longitude=...,
        captured_at_client=datetime(14, 0),  # offline time
        device_id="device-123",
        device_public_key="ed25519-key",
        ...
    ))
    assert checkin_result["status"] == "CHECKED_IN"
    
    # 2. Host confirms at 14:15 (offline)
    confirm_result = await confirm_uc.execute(ConfirmHostCommand(
        site_visit_id=...,
        mission_id=mission.id,
        host_user_id=host.id,
        latitude=..., longitude=...,
        captured_at_client=datetime(14, 15),
        ...
    ))
    assert confirm_result["status"] == "COPRESENCE_OK"
    
    # 3. Sync at 18:00 (all timestamped offline, still valid)
    # Should succeed because client_captured_at ∈ mission window
    
    # 4. Check-out
    checkout_result = await checkout_uc.execute(CheckOutCommand(
        site_visit_id=...,
        captured_at_client=datetime(14, 20),
    ))
    assert checkout_result["duration_minutes"] == 20
```

---

## **✅ Checklist final — 90/100**

```
OFFLINE GRACE
☐ captured_at_client dans tous les DTO (check-in, confirm, checkout)
☐ ensure_mission_window_client_time appliquée
☐ Tests offline scenarios (sync tardy, still valid)

GPS ACCURACY
☐ accuracy_m collecté et stocké
☐ gps_score calculé (EXCELLENT/GOOD/FAIR/POOR)
☐ Tests scoring

DEVICE BINDING
☐ MobileDevice model + ORM
☐ Device key mismatch detection
☐ Tests get_or_create logic

ANOMALY DETECTION
☐ 5+ rules implémentées (clone, too_short, poor_gps, rejeu, rapid)
☐ API endpoint /anomalies
☐ Tests chaque règle

CONFORMITÉ
☐ DPIA document rédigé + limites documentées
☐ Rétention cron job (90j images, 1-2y metadata)
☐ Charte intégrée onboarding
☐ Audit logs immuabilité testée

OBSERVABILITÉ
☐ Prometheus metrics (latency, errors)
☐ SLA p95 < 2s alerting
☐ APM/Grafana dashboard

DURÉE + GRACE
☐ Minimum 5 min visite enforced
☐ Mission grace ±10/15 minutes
☐ Tests transition logic

UX
☐ E2E test complet (offline → sync → checkout)
☐ Messages d'erreur français clairs
☐ Performance < 5s check-in, < 3s confirm, < 3s checkout

DOCUMENTATION
☐ docs/REAL_BUSINESS_EXPECTATIONS.md (FAIT)
☐ docs/V1_MATURITY_SCORE.md (FAIT)
☐ docs/BUSINESS_RULES.md (règles métier formalisées)
☐ docs/SECURITY.md (device binding, anti-replay, anomaly)
☐ docs/COMPLIANCE.md (DPIA, rétention, charte)
```

---

## 🏆 **À la fin de ces 13 jours:**

✅ **Score 90/100** → V1 prêt pour pilot  
✅ **Offline-first** → inspecteur offline jusqu'à 8h, sync après  
✅ **Anti-fraude** → 5+ anomaly rules active  
✅ **Device binding** → tracked, key mismatch detected  
✅ **Conformité** → DPIA, rétention, charte intégrée  
✅ **Observabilité** → monitoring production-ready  
✅ **UX testé** → E2E complet, messages clairs  

**= Système SIGIS V1 prêt déploiement MINESEC/MINSUB pilot**

