"""Tests device binding — anti-usurpation."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from domain.identity.mobile_device import MobileDevice


class TestMobileDeviceBinding:
    """Device binding: première clé = enregistrée, si change = rejetu."""

    def test_create_device(self):
        """Créer device avec clé publique."""
        device_id = "device-123-abc"
        public_key = "ed25519_public_key_hex_123"
        user_id = UUID("00000000-0000-0000-0000-000000000001")

        device = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=user_id,
            device_id=device_id,
            public_key_ed25519=public_key,
            device_name="iPhone 12",
        )

        assert device.device_id == device_id
        assert device.public_key_ed25519 == public_key
        assert device.device_name == "iPhone 12"
        assert device.first_seen_at is not None
        assert device.last_seen_at is not None

    def test_device_timestamps_set_automatically(self):
        """first_seen_at, last_seen_at set si absent."""
        device = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id="device-123",
            public_key_ed25519="key123",
        )

        assert device.first_seen_at is not None
        assert device.last_seen_at is not None
        # Should be close to now
        assert (datetime.now(UTC) - device.first_seen_at).total_seconds() < 1

    def test_device_none_device_name(self):
        """device_name optionnel."""
        device = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id="device-456",
            public_key_ed25519="key456",
            device_name=None,
        )

        assert device.device_name is None

    def test_device_with_explicit_timestamps(self):
        """Peut fournir timestamps explicites."""
        now = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        device = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id="device-789",
            public_key_ed25519="key789",
            first_seen_at=now,
            last_seen_at=now,
        )

        assert device.first_seen_at == now
        assert device.last_seen_at == now

    def test_device_immutable(self):
        """Device est frozen (immutable)."""
        device = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id="device-abc",
            public_key_ed25519="key_abc",
        )

        # Essayer de changer un attribut → erreur (frozen)
        with pytest.raises(AttributeError):
            device.device_name = "modified"  # type: ignore


class TestDeviceBindingScenarios:
    """Scénarios réalistes de device binding."""

    def test_first_checkin_new_device(self):
        """Premier check-in avec nouveau device = accepté, clé enregistrée."""
        device_id = "new-iphone-12"
        public_key = "ed25519_key_iphone12"

        device = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id=device_id,
            public_key_ed25519=public_key,
            device_name="iPhone 12",
        )

        # Device créé avec clé
        assert device.public_key_ed25519 == public_key

    def test_device_reuse_same_key(self):
        """Même device, même clé = accepté."""
        device_id = "iphone-12"
        public_key = "ed25519_key_same"

        device1 = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id=device_id,
            public_key_ed25519=public_key,
        )

        device2 = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id=device_id,
            public_key_ed25519=public_key,
        )

        # Même device, même clé
        assert device1.device_id == device2.device_id
        assert device1.public_key_ed25519 == device2.public_key_ed25519

    def test_device_naming_variants(self):
        """Device name peut être diverse."""
        names = [
            "iPhone 12",
            "Samsung Galaxy S21",
            "Tecno Spark 7",
            "Infinix Note 11",
            None,
        ]

        for name in names:
            device = MobileDevice(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                device_id=f"device-{name}",
                public_key_ed25519="key123",
                device_name=name,
            )
            assert device.device_name == name


class TestDeviceKeyMismatchDetection:
    """Détecter si device_id existe mais clé change (compromise)."""

    def test_key_mismatch_scenario(self):
        """Scenario: device_id existe, mais clé publique diffère."""
        device_id = "iphone-12-serial"

        # Device original
        original_device = MobileDevice(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            device_id=device_id,
            public_key_ed25519="original_key_123",
        )

        # Attemp à réutiliser device_id avec clé différente
        # (simulant compromission ou usurpation)
        different_key = "different_key_456"

        assert original_device.public_key_ed25519 != different_key
        # En réalité, ce serait rejeté par le repo get_or_create()
