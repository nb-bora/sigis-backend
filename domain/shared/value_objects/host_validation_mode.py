from enum import StrEnum


class HostValidationMode(StrEnum):
    """Mode de validation hôte V1 — invariants différents par mode (cf. cahier SIGIS)."""

    APP_GPS = "app_gps"
    QR_STATIC = "qr_static"
    SMS_SHORTCODE = "sms_shortcode"
