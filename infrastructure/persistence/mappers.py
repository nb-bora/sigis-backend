from domain.audit.audit_log_entry import AuditLogEntry
from domain.establishment.establishment import Establishment
from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus
from domain.mission.mission import Mission, MissionStatus
from domain.mission.mission_outcome import MissionOutcome
from domain.site_visit.site_visit import SiteVisit, SiteVisitStatus
from infrastructure.persistence.sqlalchemy.models import (
    AuditLogModel,
    EstablishmentModel,
    ExceptionRequestModel,
    MissionModel,
    MissionOutcomeModel,
    SiteVisitModel,
)


def establishment_to_domain(row: EstablishmentModel) -> Establishment:
    return Establishment(
        id=row.id,
        name=row.name,
        center_lat=row.center_lat,
        center_lon=row.center_lon,
        radius_strict_m=row.radius_strict_m,
        radius_relaxed_m=row.radius_relaxed_m,
        geometry_version=row.geometry_version,
        minesec_code=row.minesec_code,
        establishment_type=row.establishment_type or "other",
        contact_email=row.contact_email,
        contact_phone=row.contact_phone,
        territory_code=row.territory_code,
        parent_establishment_id=row.parent_establishment_id,
        designated_host_user_id=row.designated_host_user_id,
        geometry_validated_at=row.geometry_validated_at,
        geometry_validated_by_user_id=row.geometry_validated_by_user_id,
    )


def mission_to_domain(row: MissionModel) -> Mission:
    return Mission(
        id=row.id,
        establishment_id=row.establishment_id,
        inspector_id=row.inspector_id,
        window_start=row.window_start,
        window_end=row.window_end,
        status=MissionStatus(row.status),
        host_token=row.host_token,
        sms_code=row.sms_code,
        designated_host_user_id=row.designated_host_user_id,
        objective=row.objective,
        plan_reference=row.plan_reference,
        requires_approval=bool(row.requires_approval),
        cancellation_reason=row.cancellation_reason,
        cancelled_at=row.cancelled_at,
        cancelled_by_user_id=row.cancelled_by_user_id,
        previous_mission_id=row.previous_mission_id,
    )


def site_visit_to_domain(row: SiteVisitModel) -> SiteVisit:
    from domain.shared.value_objects.host_validation_mode import HostValidationMode

    mode = HostValidationMode(row.host_validation_mode) if row.host_validation_mode else None
    return SiteVisit(
        id=row.id,
        mission_id=row.mission_id,
        status=SiteVisitStatus(row.status),
        host_validation_mode=mode,
        checked_in_at=row.checked_in_at,
        checked_out_at=row.checked_out_at,
        inspector_lat=row.inspector_lat,
        inspector_lon=row.inspector_lon,
        host_lat=row.host_lat,
        host_lon=row.host_lon,
    )


def audit_log_to_domain(row: AuditLogModel) -> AuditLogEntry:
    return AuditLogEntry(
        id=row.id,
        created_at=row.created_at,
        actor_user_id=row.actor_user_id,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        payload_json=row.payload_json,
        request_id=row.request_id,
    )


def mission_outcome_to_domain(row: MissionOutcomeModel) -> MissionOutcome:
    return MissionOutcome(
        id=row.id,
        mission_id=row.mission_id,
        summary=row.summary,
        notes=row.notes,
        compliance_level=row.compliance_level,
        created_at=row.created_at,
        created_by_user_id=row.created_by_user_id,
    )


def exception_request_to_domain(row: ExceptionRequestModel) -> ExceptionRequest:
    return ExceptionRequest(
        id=row.id,
        mission_id=row.mission_id,
        author_user_id=row.author_user_id,
        created_at=row.created_at,
        status=ExceptionRequestStatus(row.status),
        message=row.message,
        assigned_to_user_id=row.assigned_to_user_id,
        internal_comment=row.internal_comment,
        sla_due_at=row.sla_due_at,
        attachment_url=row.attachment_url,
    )


def apply_site_visit_to_row(visit: SiteVisit, row: SiteVisitModel) -> None:
    row.status = visit.status.value
    row.host_validation_mode = (
        visit.host_validation_mode.value if visit.host_validation_mode else None
    )
    row.checked_in_at = visit.checked_in_at
    row.checked_out_at = visit.checked_out_at
    row.inspector_lat = visit.inspector_lat
    row.inspector_lon = visit.inspector_lon
    row.host_lat = visit.host_lat
    row.host_lon = visit.host_lon
