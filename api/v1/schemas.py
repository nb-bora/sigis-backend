"""Schémas Pydantic — corps des requêtes et réponses API V1."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from domain.exception_request.exception_request import ExceptionRequestStatus
from domain.identity.role import Role
from domain.shared.value_objects.host_validation_mode import HostValidationMode

# ---------------------------------------------------------------------------
# Établissements
# ---------------------------------------------------------------------------


class CreateEstablishmentBody(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=512, description="Nom officiel de l'établissement."
    )
    center_lat: float = Field(..., ge=-90, le=90, description="Latitude du centre (WGS-84).")
    center_lon: float = Field(..., ge=-180, le=180, description="Longitude du centre (WGS-84).")
    radius_strict_m: float = Field(
        ..., gt=0, description="Rayon nominal (m) — distance ≤ rayon → statut CONFIRMÉE."
    )
    radius_relaxed_m: float = Field(
        ..., gt=0, description="Rayon élargi (m) — distance dans la couronne → statut PROBABLE."
    )
    minesec_code: str | None = Field(default=None, max_length=64)
    establishment_type: str = Field(default="other", max_length=64)
    contact_email: str | None = Field(default=None, max_length=320)
    contact_phone: str | None = Field(default=None, max_length=32)
    territory_code: str | None = Field(
        default=None,
        max_length=64,
        description="Code territoire (région / académie / délégation — référentiel libre V2).",
    )
    parent_establishment_id: UUID | None = None
    designated_host_user_id: UUID | None = Field(
        default=None, description="Responsable d'accueil désigné pour cet établissement."
    )


class UpdateEstablishmentBody(BaseModel):
    """Tous les champs sont optionnels — seuls les champs fournis sont mis à jour."""

    name: str | None = Field(
        default=None, min_length=1, max_length=512, description="Nouveau nom de l'établissement."
    )
    center_lat: float | None = Field(
        default=None, ge=-90, le=90, description="Nouvelle latitude du centre."
    )
    center_lon: float | None = Field(
        default=None, ge=-180, le=180, description="Nouvelle longitude du centre."
    )
    radius_strict_m: float | None = Field(
        default=None, gt=0, description="Nouveau rayon nominal (m)."
    )
    radius_relaxed_m: float | None = Field(
        default=None, gt=0, description="Nouveau rayon élargi (m)."
    )
    minesec_code: str | None = Field(default=None, max_length=64)
    establishment_type: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=320)
    contact_phone: str | None = Field(default=None, max_length=32)
    territory_code: str | None = Field(default=None, max_length=64)
    parent_establishment_id: UUID | None = None
    designated_host_user_id: UUID | None = None


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------


class CreateMissionBody(BaseModel):
    establishment_id: UUID = Field(..., description="Identifiant de l'établissement cible.")
    inspector_id: UUID = Field(..., description="Identifiant de l'inspecteur assigné.")
    window_start: datetime = Field(
        ..., description="Début de la fenêtre horaire autorisée (ISO 8601)."
    )
    window_end: datetime = Field(..., description="Fin de la fenêtre horaire autorisée (ISO 8601).")
    sms_code: str | None = Field(
        default=None,
        max_length=32,
        description="Code SMS pour le mode de validation C (SMS_SHORTCODE). Facultatif.",
    )
    objective: str | None = Field(default=None, max_length=4000)
    plan_reference: str | None = Field(default=None, max_length=256)
    requires_approval: bool = Field(
        default=False,
        description="Si true, mission créée en draft — validation via POST .../approve.",
    )
    designated_host_user_id: UUID | None = Field(
        default=None,
        description="Surcharge du responsable d'accueil pour cette mission.",
    )


class UpdateMissionBody(BaseModel):
    """Tous les champs sont optionnels — seuls les champs fournis sont mis à jour."""

    window_start: datetime | None = Field(
        default=None, description="Nouveau début de fenêtre horaire."
    )
    window_end: datetime | None = Field(
        default=None, description="Nouvelle fin de fenêtre horaire."
    )
    status: str | None = Field(
        default=None,
        description="Nouveau statut (draft | planned | in_progress | completed | cancelled).",
    )
    sms_code: str | None = Field(
        default=None, max_length=32, description="Mise à jour du code SMS (mode C)."
    )
    designated_host_user_id: UUID | None = None
    objective: str | None = Field(default=None, max_length=4000)
    plan_reference: str | None = Field(default=None, max_length=256)


# ---------------------------------------------------------------------------
# Visites terrain
# ---------------------------------------------------------------------------


class CheckInBody(BaseModel):
    latitude: float = Field(
        ..., ge=-90, le=90, description="Latitude GPS de l'inspecteur au moment du check-in."
    )
    longitude: float = Field(
        ..., ge=-180, le=180, description="Longitude GPS de l'inspecteur au moment du check-in."
    )
    client_request_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Clé d'idempotence côté client (UUID ou chaîne unique). Permet de rejouer la requête sans double enregistrement.",
    )
    host_validation_mode: HostValidationMode = Field(
        ...,
        description=(
            "Mode de validation hôte choisi pour cette visite : "
            "app_gps (deux GPS), qr_static (QR affiché), sms_shortcode (code SMS)."
        ),
    )


class ConfirmHostBody(BaseModel):
    mission_id: UUID = Field(..., description="Identifiant de la mission concernée.")
    client_request_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Clé d'idempotence côté client.",
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitude GPS du responsable. Requis uniquement pour le mode app_gps.",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitude GPS du responsable. Requis uniquement pour le mode app_gps.",
    )
    qr_token: UUID | None = Field(
        default=None,
        description="Jeton UUID extrait du QR code de l'établissement. Requis pour le mode qr_static.",
    )
    qr_jwt: str | None = Field(
        default=None,
        description="JWT court retourné par GET /missions/{id}/host-qr-jwt (alternative au UUID).",
    )
    sms_code: str | None = Field(
        default=None,
        description="Code reçu par SMS. Requis pour le mode sms_shortcode.",
    )


class CheckOutBody(BaseModel):
    mission_id: UUID = Field(..., description="Identifiant de la mission concernée.")
    client_request_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Clé d'idempotence côté client.",
    )


# ---------------------------------------------------------------------------
# Signalements
# ---------------------------------------------------------------------------


class ExceptionBody(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Description du problème rencontré (périmètre incorrect, établissement fermé, absent, etc.).",
    )


class PatchExceptionBody(BaseModel):
    """Mise à jour signalement : statut, assignation, commentaire interne, SLA."""

    status: ExceptionRequestStatus | None = None
    assigned_to_user_id: UUID | None = None
    internal_comment: str | None = Field(default=None, max_length=8000)
    sla_due_at: datetime | None = None
    attachment_url: str | None = Field(default=None, max_length=1024)


class CancelMissionBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=4000)


class SubmitMissionOutcomeBody(BaseModel):
    summary: str = Field(..., min_length=1, max_length=8000)
    notes: str | None = Field(default=None, max_length=8000)
    compliance_level: str | None = Field(default=None, max_length=32)


class ReassignMissionBody(BaseModel):
    new_inspector_id: UUID


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class RegisterBody(BaseModel):
    email: EmailStr = Field(..., description="Adresse e-mail unique de l'utilisateur.")
    full_name: str = Field(
        ..., min_length=2, max_length=255, description="Nom complet (prénom et nom)."
    )
    phone_number: str = Field(
        ...,
        description=(
            "Numéro de téléphone camerounais à 9 chiffres (format national ou E.164 +237). "
            "Mobiles acceptés : 65X-69X (MTN, Orange, NEXTTEL). "
            "Fixes : 222XXXXXX, 233XXXXXX, 242XXXXXX, 243XXXXXX."
        ),
    )
    password: str = Field(..., min_length=8, description="Mot de passe (8 caractères minimum).")
    roles: list[Role] = Field(
        default=[Role.INSPECTOR],
        description="Liste des rôles assignés à l'utilisateur.",
    )


class LoginBody(BaseModel):
    email: EmailStr = Field(..., description="Adresse e-mail du compte.")
    password: str = Field(..., description="Mot de passe du compte.")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer à inclure dans l'en-tête Authorization.")
    token_type: str = Field(default="bearer", description="Type de jeton (toujours 'bearer').")
    user_id: UUID = Field(..., description="Identifiant unique de l'utilisateur authentifié.")
    roles: list[str] = Field(..., description="Liste des rôles de l'utilisateur.")


class ChangePasswordBody(BaseModel):
    current_password: str = Field(..., description="Mot de passe actuel.")
    new_password: str = Field(
        ..., min_length=8, description="Nouveau mot de passe (8 caractères min)."
    )


class RequestPasswordResetBody(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Adresse e-mail du compte pour lequel la réinitialisation est demandée.",
    )


class ResetPasswordBody(BaseModel):
    token: str = Field(..., description="Jeton de réinitialisation reçu par e-mail.")
    new_password: str = Field(
        ..., min_length=8, description="Nouveau mot de passe (8 caractères min)."
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    id: UUID = Field(..., description="Identifiant unique de l'utilisateur.")
    email: str = Field(..., description="Adresse e-mail.")
    full_name: str = Field(..., description="Nom complet.")
    phone_number: str = Field(
        ..., description="Numéro de téléphone en format E.164 (+237XXXXXXXXX)."
    )
    roles: list[str] = Field(..., description="Rôles attribués.")
    is_active: bool = Field(..., description="Statut du compte (actif / désactivé).")
    created_at: str = Field(..., description="Date de création du compte (ISO 8601 UTC).")


class UpdateUserBody(BaseModel):
    """Tous les champs sont optionnels — seuls les champs fournis sont mis à jour."""

    full_name: str | None = Field(
        None, min_length=2, max_length=255, description="Nouveau nom complet."
    )
    phone_number: str | None = Field(None, description="Nouveau numéro de téléphone camerounais.")
    is_active: bool | None = Field(
        None, description="Activer (true) ou désactiver (false) le compte."
    )
    roles: list[Role] | None = Field(
        None, description="Nouvelle liste de rôles (remplace l'existante)."
    )
