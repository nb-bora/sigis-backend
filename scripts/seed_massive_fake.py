"""
Génère un volume important de données factices (Cameroun / SIGIS) dans la base.

- Mot de passe unique pour tous les comptes créés : ``Changeme@2026`` (haché bcrypt).
- Fenêtre temporelle par défaut : du 8 avril 2021 au 8 avril 2026 (UTC).

**ATTENTION** : nécessite ``--wipe`` pour effacer les données existantes (développement / bench).

Usage (depuis ``sigis-backend``)::

    python -m scripts.seed_massive_fake --wipe --users 50000 --establishments 8000

Pour des millions de lignes, préférez PostgreSQL ; SQLite devient très lent et peut saturer le disque.

Tables couvertes (schéma ORM actuel) : ``users``, ``password_reset_tokens``, ``role_permissions``,
``establishments``, ``missions``, ``site_visits``, ``presence_proofs``, ``copresence_events``,
``exception_requests``, ``mission_outcomes``, ``audit_logs``, ``idempotency_records``,
``mobile_devices``, ``mobile_events``, ``used_qr_jti``, ``audit_chain_entries``.

Variables d'environnement : identiques à l'API (``SIGIS_DATABASE_URL``, etc.).
"""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
import json
import random
import secrets
import sys
from datetime import UTC, datetime, timedelta
import hashlib
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.engine import make_url

from common.password_hashing import pwd_context
from domain.identity.role import Role
from domain.identity.role_defaults import all_default_permissions
from domain.identity.value_objects.phone_number import CameroonPhoneNumber
from domain.mission.mission import MissionStatus
from domain.site_visit.site_visit import SiteVisitStatus
from infrastructure.config.settings import get_settings
from infrastructure.persistence.session import create_engine, create_session_factory
from infrastructure.persistence.sqlalchemy.models import (
    AuditChainEntryModel,
    AuditLogModel,
    CoPresenceEventModel,
    EstablishmentModel,
    ExceptionRequestModel,
    IdempotencyRecordModel,
    MissionModel,
    MissionOutcomeModel,
    MobileDeviceModel,
    MobileEventModel,
    PasswordResetTokenModel,
    PresenceProofModel,
    RolePermissionModel,
    SiteVisitModel,
    UsedQrJtiModel,
    UserModel,
)
from infrastructure.persistence.sqlalchemy.role_permission_repo import RolePermissionRepositoryImpl

SEED_PASSWORD = "Changeme@2026"

# Référentiel 8 avril 2021 → 8 avril 2026 (5 ans)
T_START = datetime(2021, 4, 8, tzinfo=UTC)
T_END = datetime(2026, 4, 8, 23, 59, 59, tzinfo=UTC)

# Villes et coordonnées (réalistes, ordre de grandeur Cameroun)
CITIES: list[tuple[str, float, float]] = [
    ("Yaoundé", 3.8480, 11.5021),
    ("Douala", 4.0511, 9.7679),
    ("Bafoussam", 5.4777, 10.4176),
    ("Bamenda", 5.9597, 10.1846),
    ("Garoua", 9.3350, 13.3900),
    ("Maroua", 10.5909, 14.3159),
    ("Ngaoundéré", 7.3167, 13.5833),
    ("Bertoua", 4.5833, 13.6833),
    ("Ébolowa", 2.9000, 11.1500),
    ("Limbe", 4.0167, 9.2167),
    ("Kribi", 2.9333, 9.9167),
    ("Buea", 4.1667, 9.2333),
]

FIRST_NAMES = (
    "Jean",
    "Marie",
    "Paul",
    "Chantal",
    "Emmanuel",
    "Grace",
    "Brigitte",
    "Samuel",
    "Esther",
    "Daniel",
    "Françoise",
    "Alain",
    "Martine",
    "Joseph",
    "Céline",
    "Patrick",
    "Audrey",
    "Fabrice",
    "Sylvie",
    "Hervé",
)

LAST_NAMES = (
    "Ndjock",
    "Fotso",
    "Kamga",
    "Mvondo",
    "Tchouassi",
    "Owona",
    "Bella",
    "Essomba",
    "Ngono",
    "Mbarga",
    "Atangana",
    "Fotsing",
    "Kouam",
    "Nguema",
    "Djeuda",
    "Talla",
    "Biya",
    "Nkoulou",
    "Abena",
    "Mballa",
)

EST_TYPES = ("primary", "secondary", "lycee", "college", "other")


def _is_sqlite(database_url: str) -> bool:
    return make_url(database_url).drivername.startswith("sqlite")


def _batch_rows_for_sqlite(n_columns: int) -> int:
    """SQLite limite souvent à 999 variables par requête."""
    return max(1, min(64, 999 // max(n_columns, 1)))


def _random_ts() -> datetime:
    span = (T_END - T_START).total_seconds()
    return T_START + timedelta(seconds=random.random() * span)


def _role_for_index(i: int) -> str:
    r = random.Random(i * 7919 + 17)
    x = r.random()
    if x < 0.003:
        return Role.SUPER_ADMIN.value
    if x < 0.012:
        return Role.NATIONAL_ADMIN.value
    if x < 0.12:
        return Role.REGIONAL_SUPERVISOR.value
    if x < 0.55:
        return Role.INSPECTOR.value
    return Role.HOST.value


def _e164_mobile_from_index(i: int) -> str:
    """Mobile valide PNN (préfixe 66…) — évite les plages réservées au seed démo (65…)."""
    tail = i % 10_000_000
    national = f"66{tail:07d}"
    return CameroonPhoneNumber(national).e164


def _pick_mission_status(rng: random.Random) -> str:
    w = rng.random()
    if w < 0.08:
        return MissionStatus.DRAFT.value
    if w < 0.22:
        return MissionStatus.PLANNED.value
    if w < 0.28:
        return MissionStatus.IN_PROGRESS.value
    if w < 0.18:
        return MissionStatus.CANCELLED.value
    return MissionStatus.COMPLETED.value


def rng_choice_in_progress(rng: random.Random) -> str:
    return rng.choice(
        (
            SiteVisitStatus.CHECKED_IN.value,
            SiteVisitStatus.PENDING_HOST.value,
            SiteVisitStatus.SCHEDULED.value,
            SiteVisitStatus.COPRESENCE_OK.value,
        )
    )


async def _wipe_data(session, dialect_sqlite: bool) -> None:
    """Supprime les données métier (pas le schéma)."""
    if dialect_sqlite:
        await session.execute(text("PRAGMA foreign_keys=OFF"))
    await session.execute(text("DELETE FROM mobile_events"))
    await session.execute(text("DELETE FROM used_qr_jti"))
    await session.execute(text("DELETE FROM mobile_devices"))
    await session.execute(text("DELETE FROM audit_chain_entries"))
    await session.execute(text("DELETE FROM audit_logs"))
    await session.execute(text("DELETE FROM mission_outcomes"))
    await session.execute(text("DELETE FROM exception_requests"))
    await session.execute(text("DELETE FROM presence_proofs"))
    await session.execute(text("DELETE FROM copresence_events"))
    await session.execute(text("DELETE FROM site_visits"))
    await session.execute(
        text(
            "UPDATE missions SET previous_mission_id = NULL, "
            "cancelled_by_user_id = NULL, designated_host_user_id = NULL"
        )
    )
    await session.execute(text("DELETE FROM missions"))
    await session.execute(
        text(
            "UPDATE establishments SET parent_establishment_id = NULL, "
            "designated_host_user_id = NULL, geometry_validated_by_user_id = NULL"
        )
    )
    await session.execute(text("DELETE FROM establishments"))
    await session.execute(text("DELETE FROM password_reset_tokens"))
    await session.execute(text("DELETE FROM idempotency_records"))
    await session.execute(text("DELETE FROM role_permissions"))
    await session.execute(text("DELETE FROM users"))
    if dialect_sqlite:
        await session.execute(text("PRAGMA foreign_keys=ON"))
    await session.commit()


async def _seed_role_permissions(session) -> None:
    repo = RolePermissionRepositoryImpl(session)
    n1 = await repo.seed_defaults(all_default_permissions())
    n2 = await repo.ensure_catalog_permissions_present()
    await session.commit()
    print(f"role_permissions : +{n1} défauts, +{n2} catalogue.")


async def _print_table_counts(session_factory) -> None:
    """Affiche le nombre de lignes par table (vérif post-seed)."""
    tables: list[tuple[str, type]] = [
        ("users", UserModel),
        ("password_reset_tokens", PasswordResetTokenModel),
        ("role_permissions", RolePermissionModel),
        ("establishments", EstablishmentModel),
        ("missions", MissionModel),
        ("site_visits", SiteVisitModel),
        ("presence_proofs", PresenceProofModel),
        ("copresence_events", CoPresenceEventModel),
        ("exception_requests", ExceptionRequestModel),
        ("mission_outcomes", MissionOutcomeModel),
        ("audit_logs", AuditLogModel),
        ("idempotency_records", IdempotencyRecordModel),
        ("mobile_devices", MobileDeviceModel),
        ("mobile_events", MobileEventModel),
        ("used_qr_jti", UsedQrJtiModel),
        ("audit_chain_entries", AuditChainEntryModel),
    ]
    async with session_factory() as session:
        print("Récapitulatif des lignes par table :")
        for name, model in tables:
            n = await session.scalar(select(func.count()).select_from(model.__table__))
            print(f"  {name}: {n}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed massif SIGIS (données factices).")
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Efface toutes les données des tables applicatives avant insertion.",
    )
    parser.add_argument("--users", type=int, default=10_000, help="Nombre d'utilisateurs.")
    parser.add_argument(
        "--establishments", type=int, default=0, help="Nombre d'établissements (0 = auto)."
    )
    parser.add_argument(
        "--missions",
        type=int,
        default=0,
        help="Nombre de missions (0 = auto ~ min(users*8, 2_000_000)).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Graine RNG reproductible.")
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Ne pas exécuter les COUNT(*) par table en fin de script (bases très volumineuses).",
    )
    args = parser.parse_args()

    if not args.wipe:
        print(
            "Refus : ce script est destructif. Relancez avec --wipe pour confirmer "
            "la suppression des données existantes.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if args.users < 10:
        print("--users doit être >= 10.", file=sys.stderr)
        raise SystemExit(2)

    random.seed(args.seed)

    n_est = args.establishments or max(50, args.users // 5)
    n_missions = args.missions or min(args.users * 8, 2_000_000)

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    dialect_sqlite = _is_sqlite(settings.database_url)

    pwd_hash = pwd_context.hash(SEED_PASSWORD)
    print(f"Hachage bcrypt du mot de passe commun généré (longueur {len(pwd_hash)}).")

    async with session_factory() as session:
        if dialect_sqlite:
            await session.execute(text("PRAGMA journal_mode=WAL"))
            await session.execute(text("PRAGMA synchronous=NORMAL"))
            await session.execute(text("PRAGMA cache_size=-200000"))
            await session.commit()

        await _wipe_data(session, dialect_sqlite)
        await _seed_role_permissions(session)

    # --- Utilisateurs + jetons reset (échantillon) ---
    inspector_ids: list[UUID] = []
    host_ids: list[UUID] = []
    admin_ids: list[UUID] = []
    all_user_ids: list[UUID] = []

    user_cols = 9
    ub = _batch_rows_for_sqlite(user_cols) if dialect_sqlite else 800

    async with session_factory() as session:
        batch: list[dict] = []
        phone_i = 10_000_000  # décale la plage 66… pour limiter les collisions avec seed démo

        for i in range(args.users):
            uid = uuid4()
            all_user_ids.append(uid)
            role = _role_for_index(i)
            if role == Role.INSPECTOR.value:
                inspector_ids.append(uid)
            elif role == Role.HOST.value:
                host_ids.append(uid)
            elif role in (Role.SUPER_ADMIN.value, Role.NATIONAL_ADMIN.value, Role.REGIONAL_SUPERVISOR.value):
                admin_ids.append(uid)

            fn = FIRST_NAMES[i % len(FIRST_NAMES)]
            ln = LAST_NAMES[(i * 7) % len(LAST_NAMES)]
            batch.append(
                {
                    "id": uid,
                    "email": f"user{i:09d}@seed.bulk.sigis.cm",
                    "full_name": f"{fn} {ln}",
                    "phone_number": _e164_mobile_from_index(phone_i + i),
                    "hashed_password": pwd_hash,
                    "role": role,
                    "is_active": True,
                    "created_at": _random_ts(),
                    "updated_at": _random_ts(),
                }
            )
            if len(batch) >= ub:
                await session.execute(insert(UserModel), batch)
                await session.commit()
                batch.clear()
        if batch:
            await session.execute(insert(UserModel), batch)
            await session.commit()

        n_pr = min(50_000, max(100, args.users // 3))
        pr_batch: list[dict] = []
        pr_ub = _batch_rows_for_sqlite(6) if dialect_sqlite else 800
        for _ in range(n_pr):
            uid = random.choice(all_user_ids)
            raw = secrets.token_bytes(32)
            pr_batch.append(
                {
                    "id": uuid4(),
                    "user_id": uid,
                    "token_hash": hashlib.sha256(raw).hexdigest(),
                    "expires_at": _random_ts() + timedelta(days=1, hours=random.randint(0, 48)),
                    "used": random.random() < 0.35,
                    "created_at": _random_ts(),
                }
            )
            if len(pr_batch) >= pr_ub:
                await session.execute(insert(PasswordResetTokenModel), pr_batch)
                await session.commit()
                pr_batch.clear()
        if pr_batch:
            await session.execute(insert(PasswordResetTokenModel), pr_batch)
            await session.commit()

    if not inspector_ids:
        print("Aucun inspecteur généré — impossible de créer des missions.", file=sys.stderr)
        raise SystemExit(3)
    if not host_ids:
        print("Aucun hôte généré — les établissements n'auront pas d'hôte désigné.", file=sys.stderr)

    print(f"Utilisateurs : {len(all_user_ids)} (inspecteurs : {len(inspector_ids)}).")

    # --- Établissements ---
    establishment_ids: list[UUID] = []
    est_cols = 14
    eb = _batch_rows_for_sqlite(est_cols) if dialect_sqlite else 400

    async with session_factory() as session:
        batch = []
        for j in range(n_est):
            eid = uuid4()
            establishment_ids.append(eid)
            city, clat, clon = CITIES[j % len(CITIES)]
            jitter_lat = clat + random.uniform(-0.04, 0.04)
            jitter_lon = clon + random.uniform(-0.04, 0.04)
            minesec = f"{100000 + (j % 899999)}CE{10 + (j % 89)}"
            host_uid = random.choice(host_ids) if host_ids else None
            validator = random.choice(admin_ids) if admin_ids else None
            kind = EST_TYPES[j % len(EST_TYPES)]
            name = (
                f"{'Lycée' if kind == 'lycee' else 'Collège' if kind == 'college' else 'École'} "
                f"{LAST_NAMES[j % len(LAST_NAMES)]} — {city}"
            )
            batch.append(
                {
                    "id": eid,
                    "name": name,
                    "center_lat": jitter_lat,
                    "center_lon": jitter_lon,
                    "radius_strict_m": 80.0 + random.uniform(0, 40),
                    "radius_relaxed_m": 180.0 + random.uniform(0, 60),
                    "geometry_version": 1,
                    "minesec_code": minesec,
                    "establishment_type": kind,
                    "contact_email": f"contact{j:06d}@etab.seed.sigis.cm",
                    "contact_phone": _e164_mobile_from_index(20_000_000 + j),
                    "territory_code": f"CM-CE-{city[:3].upper()}",
                    "parent_establishment_id": None,
                    "designated_host_user_id": host_uid,
                    "geometry_validated_at": _random_ts() if validator else None,
                    "geometry_validated_by_user_id": validator,
                }
            )
            if len(batch) >= eb:
                await session.execute(insert(EstablishmentModel), batch)
                await session.commit()
                batch.clear()
        if batch:
            await session.execute(insert(EstablishmentModel), batch)
            await session.commit()

    # Hiérarchie établissements : ~10 % des lignes pointent vers un parent (autre établissement).
    async with session_factory() as session:
        n_parent_links = min(max(5, n_est // 10), 10_000)
        if len(establishment_ids) >= 3:
            for _ in range(n_parent_links):
                cid = random.choice(establishment_ids)
                candidates = [e for e in establishment_ids if e != cid]
                pid = random.choice(candidates)
                await session.execute(
                    update(EstablishmentModel)
                    .where(EstablishmentModel.id == cid)
                    .values(parent_establishment_id=pid)
                )
        await session.commit()

    print(f"Établissements : {len(establishment_ids)}.")

    # --- Missions + visites + satellites (par lots) ---
    mission_batch_size = 500 if dialect_sqlite else 2000
    processed = 0
    chain_prev: str | None = None
    prev_mission_by_inspector: dict[UUID, UUID] = {}

    async with session_factory() as session:
        while processed < n_missions:
            chunk = min(mission_batch_size, n_missions - processed)
            m_rows: list[dict] = []
            sv_rows: list[dict] = []
            pp_rows: list[dict] = []
            cp_rows: list[dict] = []
            ex_rows: list[dict] = []
            mo_rows: list[dict] = []
            al_rows: list[dict] = []
            idem_rows: list[dict] = []
            qr_rows: list[dict] = []
            ac_rows: list[dict] = []

            for k in range(chunk):
                g = random.Random(processed + k + args.seed * 1000)
                mid = uuid4()
                eid = random.choice(establishment_ids)
                insp = random.choice(inspector_ids)

                ws = _random_ts()
                we = ws + timedelta(hours=g.randint(2, 72))
                ms = _pick_mission_status(g)
                host_tok = uuid4()
                sms = f"{g.randint(100000, 999999)}" if g.random() < 0.4 else None
                dhost = random.choice(host_ids) if host_ids and g.random() < 0.7 else None

                cancel_reason = None
                cancelled_at = None
                cancelled_by = None
                if ms == MissionStatus.CANCELLED.value:
                    cancel_reason = random.choice(
                        ("Météo", "Indisponibilité établissement", "Report administratif", "Urgence terrain")
                    )
                    cancelled_at = ws + timedelta(minutes=g.randint(30, 300))
                    cancelled_by = random.choice(admin_ids) if admin_ids else None

                prev_m: UUID | None = None
                if g.random() < 0.08 and insp in prev_mission_by_inspector:
                    prev_m = prev_mission_by_inspector[insp]

                m_rows.append(
                    {
                        "id": mid,
                        "establishment_id": eid,
                        "inspector_id": insp,
                        "window_start": ws,
                        "window_end": we,
                        "status": ms,
                        "host_token": host_tok,
                        "sms_code": sms,
                        "designated_host_user_id": dhost,
                        "objective": random.choice(
                            (
                                "Contrôle pédagogique et hygiène",
                                "Vérification des effectifs et registres",
                                "Suivi plan national qualité",
                                "Inspection infrastructure",
                            )
                        ),
                        "plan_reference": f"PLN-{ws.year}-{g.randint(100, 999)}",
                        "requires_approval": g.random() < 0.12,
                        "cancellation_reason": cancel_reason,
                        "cancelled_at": cancelled_at,
                        "cancelled_by_user_id": cancelled_by,
                        "previous_mission_id": prev_m,
                    }
                )

                vs = (
                    SiteVisitStatus.COMPLETED.value
                    if ms == MissionStatus.COMPLETED.value
                    else SiteVisitStatus.CANCELLED.value
                    if ms == MissionStatus.CANCELLED.value
                    else (
                        SiteVisitStatus.SCHEDULED.value
                        if ms in (MissionStatus.DRAFT.value, MissionStatus.PLANNED.value)
                        else rng_choice_in_progress(g)
                    )
                )
                hmode = g.choice(("app_gps", "qr_static", "sms_shortcode"))

                svid = uuid4()
                _city, clat, clon = CITIES[hash(str(eid)) % len(CITIES)]
                cin = cout = None
                ila = clat + g.uniform(-0.002, 0.002)
                ilo = clon + g.uniform(-0.002, 0.002)
                hla = clat + g.uniform(-0.001, 0.001)
                hlo = clon + g.uniform(-0.001, 0.001)
                if vs in (
                    SiteVisitStatus.CHECKED_IN.value,
                    SiteVisitStatus.PENDING_HOST.value,
                    SiteVisitStatus.COPRESENCE_OK.value,
                    SiteVisitStatus.CHECKED_OUT.value,
                    SiteVisitStatus.COMPLETED.value,
                ):
                    cin = ws + timedelta(minutes=g.randint(5, 120))
                if vs in (SiteVisitStatus.COMPLETED.value, SiteVisitStatus.CHECKED_OUT.value):
                    cout = (cin or ws) + timedelta(minutes=g.randint(30, 240))

                sv_rows.append(
                    {
                        "id": svid,
                        "mission_id": mid,
                        "status": vs,
                        "host_validation_mode": hmode,
                        "checked_in_at": cin,
                        "checked_out_at": cout,
                        "inspector_lat": ila,
                        "inspector_lon": ilo,
                        "host_lat": hla,
                        "host_lon": hlo,
                    }
                )

                if cin and vs != SiteVisitStatus.CANCELLED.value:
                    for _ in range(g.randint(1, 3)):
                        pp_rows.append(
                            {
                                "id": uuid4(),
                                "site_visit_id": svid,
                                "actor_user_id": insp,
                                "recorded_at": cin + timedelta(seconds=g.randint(10, 300)),
                                "latitude": ila + g.uniform(-0.0003, 0.0003),
                                "longitude": ilo + g.uniform(-0.0003, 0.0003),
                                "geofence_status": g.choice(("OK", "APPROXIMATE", "REJECTED")),
                            }
                        )

                if vs == SiteVisitStatus.COPRESENCE_OK.value or (
                    vs == SiteVisitStatus.COMPLETED.value and g.random() < 0.85
                ):
                    cp_rows.append(
                        {
                            "id": uuid4(),
                            "site_visit_id": svid,
                            "validated_at": (cin or ws) + timedelta(minutes=g.randint(5, 60)),
                            "host_validation_mode": hmode,
                        }
                    )

                if g.random() < 0.04:
                    ex_rows.append(
                        {
                            "id": uuid4(),
                            "mission_id": mid,
                            "author_user_id": insp,
                            "created_at": _random_ts(),
                            "status": random.choice(("new", "acknowledged", "resolved", "escalated")),
                            "message": random.choice(
                                (
                                    "Retard dû aux intempéries",
                                    "Absence du responsable d'accueil",
                                    "Problème de connexion sur le terrain",
                                    "Demande de prolongation de fenêtre",
                                )
                            ),
                            "assigned_to_user_id": random.choice(admin_ids) if admin_ids else None,
                            "internal_comment": (
                                "Vu avec la délégation — suivi sous 48 h."
                                if g.random() < 0.45
                                else None
                            ),
                            "sla_due_at": _random_ts() + timedelta(days=3),
                            "attachment_url": (
                                f"https://storage.seed.sigis.local/exc/{uuid4()}.pdf"
                                if g.random() < 0.2
                                else None
                            ),
                        }
                    )

                if ms == MissionStatus.COMPLETED.value and g.random() < 0.75:
                    mo_rows.append(
                        {
                            "id": uuid4(),
                            "mission_id": mid,
                            "summary": random.choice(
                                (
                                    "Visite conforme aux attendus du plan national.",
                                    "Points d'amélioration mineurs notés.",
                                    "Actions correctives demandées sous 30 jours.",
                                )
                            ),
                            "notes": "Compte rendu synthétique (données de test).",
                            "compliance_level": random.choice(
                                ("conforme", "partiel", "non_conforme", "hors_cadre")
                            ),
                            "created_at": we + timedelta(hours=g.randint(1, 48)),
                            "created_by_user_id": insp,
                        }
                    )

                if g.random() < 0.02:
                    al_rows.append(
                        {
                            "id": uuid4(),
                            "created_at": _random_ts(),
                            "actor_user_id": random.choice(admin_ids) if admin_ids else insp,
                            "action": random.choice(("MISSION_UPDATE", "VISIT_CHECKIN", "USER_LOGIN")),
                            "resource_type": "mission",
                            "resource_id": str(mid),
                            "payload_json": json.dumps({"seed": True, "mission_id": str(mid)}),
                            "request_id": secrets.token_hex(8),
                        }
                    )

                if g.random() < 0.005:
                    idem_rows.append(
                        {
                            "id": uuid4(),
                            "scope": "mobile_sync",
                            "client_key": f"idem-{mid}-{g.randint(0, 99999)}",
                            "created_at": _random_ts(),
                            "response_body": '{"ok":true}',
                        }
                    )

                if g.random() < 0.25:
                    qr_rows.append(
                        {
                            "jti": secrets.token_hex(16),
                            "mission_id": mid,
                            "consumed_at": ws + timedelta(minutes=g.randint(1, 180)),
                        }
                    )

                # Chaîne d'audit (échantillon)
                if g.random() < 0.003:
                    ev_hash = secrets.token_hex(32)
                    entry_hash = sha256(f"{chain_prev or ''}:{ev_hash}".encode()).hexdigest()
                    ac_rows.append(
                        {
                            "id": uuid4(),
                            "created_at": _random_ts(),
                            "resource_type": "mission",
                            "resource_id": str(mid),
                            "prev_hash": chain_prev,
                            "entry_hash": entry_hash,
                        }
                    )
                    chain_prev = entry_hash

            # Inserts ordonnés
            await session.execute(insert(MissionModel), m_rows)
            await session.execute(insert(SiteVisitModel), sv_rows)
            if pp_rows:
                pb = _batch_rows_for_sqlite(7) if dialect_sqlite else 1000
                for i0 in range(0, len(pp_rows), pb):
                    await session.execute(insert(PresenceProofModel), pp_rows[i0 : i0 + pb])
            if cp_rows:
                await session.execute(insert(CoPresenceEventModel), cp_rows)
            if ex_rows:
                await session.execute(insert(ExceptionRequestModel), ex_rows)
            if mo_rows:
                await session.execute(insert(MissionOutcomeModel), mo_rows)
            if al_rows:
                await session.execute(insert(AuditLogModel), al_rows)
            if idem_rows:
                await session.execute(insert(IdempotencyRecordModel), idem_rows)
            if qr_rows:
                await session.execute(insert(UsedQrJtiModel), qr_rows)
            if ac_rows:
                await session.execute(insert(AuditChainEntryModel), ac_rows)

            await session.commit()
            last_by_insp: dict[UUID, UUID] = {}
            for m in m_rows:
                last_by_insp[m["inspector_id"]] = m["id"]
            prev_mission_by_inspector.update(last_by_insp)
            processed += chunk
            if processed % (mission_batch_size * 5) == 0 or processed >= n_missions:
                print(f"  missions insérées : {processed} / {n_missions}")

        await session.commit()

    # --- Appareils mobiles + événements (échantillon) ---
    n_event_pairs = min(50_000, max(500, n_missions // 10))

    async with session_factory() as session:
        dev_by_insp: dict[UUID, UUID] = {}
        md_rows: list[dict] = []
        for insp in inspector_ids:
            did = uuid4()
            dev_by_insp[insp] = did
            md_rows.append(
                {
                    "id": did,
                    "user_id": insp,
                    "public_key_ed25519": secrets.token_hex(32),
                    "created_at": _random_ts(),
                    "revoked_at": (_random_ts() if random.random() < 0.06 else None),
                }
            )
        if md_rows:
            mb = _batch_rows_for_sqlite(5) if dialect_sqlite else 1000
            for i0 in range(0, len(md_rows), mb):
                await session.execute(insert(MobileDeviceModel), md_rows[i0 : i0 + mb])
            await session.commit()

        stmt = (
            select(MissionModel.id, SiteVisitModel.id, MissionModel.inspector_id)
            .join(SiteVisitModel, SiteVisitModel.mission_id == MissionModel.id)
            .order_by(func.random())
            .limit(n_event_pairs)
        )
        res = await session.execute(stmt)
        triples = list(res.all())

        me_rows: list[dict] = []
        for mid, svid, insp in triples:
            if insp not in dev_by_insp:
                continue
            did = dev_by_insp[insp]
            for _ in range(random.randint(1, 2)):
                ev_hash = secrets.token_hex(32)
                et = random.choice(("CHECK_IN", "HOST_CONFIRM", "CHECK_OUT"))
                cap = _random_ts()
                rec = cap + timedelta(seconds=random.randint(0, 120))
                _city, c_lat, c_lon = CITIES[hash(str(mid)) % len(CITIES)]
                raw_payload = json.dumps(
                    {"type": et, "mission_id": str(mid), "seed": True},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                has_selfie = random.random() < 0.28
                w = random.randint(720, 1080) if has_selfie else None
                h = random.randint(960, 1920) if has_selfie else None
                me_rows.append(
                    {
                        "id": uuid4(),
                        "event_type": et,
                        "mission_id": mid,
                        "site_visit_id": svid,
                        "actor_user_id": insp,
                        "device_id": did,
                        "client_request_id": secrets.token_hex(16),
                        "captured_at_client": cap,
                        "received_at_server": rec,
                        "gps_lat": c_lat + random.uniform(-0.05, 0.05),
                        "gps_lon": c_lon + random.uniform(-0.05, 0.05),
                        "gps_accuracy_m": 8.0 + random.uniform(0, 25),
                        "gps_provider": "gps",
                        "selfie_sha256": (secrets.token_hex(32) if has_selfie else None),
                        "selfie_mime": ("image/jpeg" if has_selfie else None),
                        "selfie_w": w,
                        "selfie_h": h,
                        "prev_event_hash": None,
                        "event_hash": ev_hash,
                        "signature_ed25519": secrets.token_hex(64),
                        "raw_json": raw_payload,
                    }
                )
        if me_rows:
            by_dev: dict[UUID, list[dict]] = defaultdict(list)
            for row in me_rows:
                by_dev[row["device_id"]].append(row)
            for rows in by_dev.values():
                rows.sort(key=lambda r: r["captured_at_client"])
                prev_h: str | None = None
                for r in rows:
                    r["prev_event_hash"] = prev_h
                    prev_h = r["event_hash"]
            me_b = _batch_rows_for_sqlite(18) if dialect_sqlite else 800
            for i0 in range(0, len(me_rows), me_b):
                await session.execute(insert(MobileEventModel), me_rows[i0 : i0 + me_b])
        await session.commit()

    print("Terminé.")
    print(f"Mot de passe de tous les comptes seed : {SEED_PASSWORD}")
    if not args.no_summary:
        await _print_table_counts(session_factory)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
