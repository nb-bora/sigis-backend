"""Schémas Pydantic — corps des requêtes et réponses API V1."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

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
        description="Nouveau statut (planned | in_progress | completed | cancelled).",
    )
    sms_code: str | None = Field(
        default=None, max_length=32, description="Mise à jour du code SMS (mode C)."
    )


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
