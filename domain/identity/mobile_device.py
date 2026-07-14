"""Device binding — une app/device = une clé publique (anti-usurpation)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True)
class MobileDevice:
    """Représente un device mobile de l'utilisateur.

    Device binding: première clé publique vue = enregistrée.
    Si clé change later = possible compromise (rejeté).
    """

    id: UUID
    user_id: UUID
    device_id: str  # UUID from mobile app (unique per device)
    public_key_ed25519: str  # hex-encoded Ed25519 public key
    device_name: str | None = None  # "iPhone 12", "Tecno Spark", etc.
    first_seen_at: datetime = None  # type: ignore
    last_seen_at: datetime = None  # type: ignore

    def __post_init__(self) -> None:
        """Set defaults si absent."""
        if self.first_seen_at is None:
            object.__setattr__(self, "first_seen_at", datetime.now(UTC))
        if self.last_seen_at is None:
            object.__setattr__(self, "last_seen_at", datetime.now(UTC))
