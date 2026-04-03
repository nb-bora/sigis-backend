from domain.establishment.establishment import Establishment
from domain.mission.mission import Mission, MissionStatus
from domain.site_visit.site_visit import SiteVisit, SiteVisitStatus
from infrastructure.persistence.sqlalchemy.models import (
    EstablishmentModel,
    MissionModel,
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
