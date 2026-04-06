"""
Création idempotente de comptes de démonstration (un par rôle).

Sans doublon : si l'e-mail « préféré » existe déjà avec le même rôle, on ignore ;
si l'e-mail est pris par un autre rôle, on essaie ``*.1``, ``*.2``, … ;
si le téléphone est pris, on prend le prochain numéro mobile valide libre.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from common.password_hashing import pwd_context
from domain.identity.role import Role
from domain.identity.user import User
from domain.identity.value_objects.phone_number import CameroonPhoneNumber
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork

SEED_DEFAULT_PASSWORD = "Changeme@2026"

# (rôle, e-mail préféré, nom affiché, 9 chiffres nationaux préférés pour le téléphone)
_SEED_ROWS: tuple[tuple[Role, str, str, str], ...] = (
    (Role.SUPER_ADMIN, "super.admin@sigis.seed", "Super Admin (seed)", "650000001"),
    (Role.NATIONAL_ADMIN, "national.admin@sigis.seed", "National Admin (seed)", "650000002"),
    (
        Role.REGIONAL_SUPERVISOR,
        "regional.supervisor@sigis.seed",
        "Regional Supervisor (seed)",
        "650000003",
    ),
    (Role.INSPECTOR, "inspector.seed@sigis.seed", "Inspecteur (seed)", "650000004"),
    (Role.HOST, "host.seed@sigis.seed", "Hôte (seed)", "650000005"),
)


@dataclass(frozen=True)
class SeedAccountResult:
    role: str
    email: str
    status: str  # "created" | "skipped"
    detail: str


def _email_variants(preferred: str) -> list[str]:
    """Préféré puis local.1, local.2, … avant @."""
    local, _, domain = preferred.partition("@")
    out = [preferred]
    for i in range(1, 50):
        out.append(f"{local}.{i}@{domain}")
    return out


async def _first_free_phone(uow: SqlAlchemyUnitOfWork, start_national: str) -> str:
    """Parcourt des mobiles valides à partir des 9 chiffres donnés puis incrémente."""
    assert uow.users is not None
    start = int(start_national)
    for offset in range(500):
        candidate = str(start + offset)
        if len(candidate) != 9:
            continue
        try:
            vo = CameroonPhoneNumber(candidate)
        except Exception:
            continue
        if await uow.users.get_by_phone(vo.e164) is None:
            return vo.e164
    raise RuntimeError("Impossible d'allouer un numéro de téléphone libre pour le seed.")


async def execute_seed_demo_users(uow: SqlAlchemyUnitOfWork) -> tuple[list[SeedAccountResult], str]:
    """
    Retourne (résultats par rôle, mot de passe commun pour les comptes créés).
    """
    assert uow.users is not None
    pwd_hash = pwd_context.hash(SEED_DEFAULT_PASSWORD)
    now = datetime.now(UTC)
    results: list[SeedAccountResult] = []

    for role, preferred_email, full_name, phone_pref in _SEED_ROWS:
        chosen_email: str | None = None
        already_seeded = False
        for em in _email_variants(preferred_email):
            em = em.lower()
            existing = await uow.users.get_by_email(em)
            if existing is None:
                chosen_email = em
                break
            if existing.role == role:
                results.append(
                    SeedAccountResult(
                        role=role.value,
                        email=em,
                        status="skipped",
                        detail="Compte déjà présent pour ce rôle.",
                    )
                )
                already_seeded = True
                break
            # E-mail pris par un autre rôle : essayer la variante suivante
        if already_seeded:
            continue
        if chosen_email is None:
            results.append(
                SeedAccountResult(
                    role=role.value,
                    email=preferred_email,
                    status="skipped",
                    detail="Aucune variante d'e-mail libre (trop de conflits).",
                )
            )
            continue

        phone_e164 = await _first_free_phone(uow, phone_pref)
        user = User(
            id=uuid.uuid4(),
            email=chosen_email,
            full_name=full_name,
            phone_number=phone_e164,
            hashed_password=pwd_hash,
            role=role,
            is_active=True,
            created_at=now,
            updated_at=None,
        )
        await uow.users.create(user)
        results.append(
            SeedAccountResult(
                role=role.value,
                email=chosen_email,
                status="created",
                detail="Compte créé.",
            )
        )

    return results, SEED_DEFAULT_PASSWORD
