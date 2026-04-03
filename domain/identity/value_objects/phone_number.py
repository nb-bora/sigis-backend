"""
Objet valeur : numéro de téléphone camerounais.

Conforme au Plan de Numérotage National (PNN) de l'ART Cameroun,
communication du 6 novembre 2014 — passage de 8 à 9 chiffres.

Format E.164 stocké : +237XXXXXXXXX (12 caractères)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Numéros mobiles (S = 6)
  ────────────────────────────────────────
  65X XXXXXX  →  MTN (650-654) / Orange (655-659)
  66X XXXXXX  →  NEXTTEL (ex Viettel)
  67X XXXXXX  →  MTN Cameroon
  69X XXXXXX  →  Orange Cameroun

  Numéros fixes (S = 2)
  ────────────────────────────────────────
  222 XXXXXX  →  Camtel (zone Yaoundé)
  233 XXXXXX  →  Camtel (zone Douala)
  242 XXXXXX  →  Camtel CDMA
  243 XXXXXX  →  Camtel CDMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import re

from domain.errors import DomainError

# ── Regex ────────────────────────────────────────────────────────────────────

# 9 chiffres nationaux significatifs
_MOBILE_RE = re.compile(r"^6[5679]\d{7}$")
_FIXED_RE = re.compile(r"^(222|233|242|243)\d{6}$")

# Indicatif pays camerounais (optionnel à la saisie)
_COUNTRY_PREFIX_RE = re.compile(r"^\+?237")

# Séparateurs visuels tolérés à la saisie : espaces, tirets, points
_STRIP_RE = re.compile(r"[\s\-.()\u00a0]+")


class CameroonPhoneNumber:
    """
    Représente un numéro de téléphone camerounais validé (mobile ou fixe).

    Accepte à la saisie :
      • avec ou sans indicatif pays : +237 ou 237
      • séparateurs visuels : espaces, tirets, points, parenthèses
      • 8 ou 9 chiffres nationaux (les anciens numéros à 8 chiffres
        mobiles ne sont plus valides depuis nov. 2014)

    Lève ``InvalidPhoneNumber`` si le numéro ne correspond à aucun
    bloc du PNN camerounais.
    """

    __slots__ = ("_e164",)

    def __init__(self, raw: str) -> None:
        digits = self._normalize(raw)
        if not (_MOBILE_RE.match(digits) or _FIXED_RE.match(digits)):
            raise InvalidPhoneNumber(
                f"Numéro invalide : « {raw} ». "
                "Seuls les numéros camerounais à 9 chiffres sont acceptés "
                "(mobiles : 65X-69X ; fixes : 222, 233, 242, 243)."
            )
        self._e164 = f"+237{digits}"

    # ── public ───────────────────────────────────────────────────────────────

    @property
    def e164(self) -> str:
        """Format international E.164 : +237XXXXXXXXX."""
        return self._e164

    @property
    def national(self) -> str:
        """9 chiffres nationaux sans indicatif pays."""
        return self._e164[4:]  # retire "+237"

    @property
    def is_mobile(self) -> bool:
        return self.national.startswith("6")

    @property
    def is_whatsapp_eligible(self) -> bool:
        """WhatsApp est disponible sur les lignes mobiles camerounaises."""
        return self.is_mobile

    @property
    def operator(self) -> str:
        n = self.national
        if n.startswith("66"):
            return "NEXTTEL"
        if n.startswith("67") or n[:3] in {"650", "651", "652", "653", "654"}:
            return "MTN"
        if n.startswith("69") or n[:3] in {"655", "656", "657", "658", "659"}:
            return "ORANGE"
        if n.startswith("222") or n.startswith("233"):
            return "CAMTEL_FIXE"
        if n.startswith("242") or n.startswith("243"):
            return "CAMTEL_CDMA"
        return "INCONNU"

    # ── display ──────────────────────────────────────────────────────────────

    def __str__(self) -> str:
        return self._e164

    def __repr__(self) -> str:
        return f"CameroonPhoneNumber('{self._e164}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CameroonPhoneNumber):
            return self._e164 == other._e164
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._e164)

    # ── private ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(raw: str) -> str:
        """Supprime séparateurs et indicatif pays → 9 chiffres bruts."""
        cleaned = _STRIP_RE.sub("", raw.strip())
        # Retire l'indicatif pays si présent (+237 ou 237)
        cleaned = _COUNTRY_PREFIX_RE.sub("", cleaned)
        if not cleaned.isdigit():
            raise InvalidPhoneNumber(
                f"Numéro invalide : « {raw} » (caractères non numériques détectés)."
            )
        if len(cleaned) != 9:
            raise InvalidPhoneNumber(
                f"Numéro invalide : « {raw} » — le numéro national doit avoir "
                f"9 chiffres (reçu : {len(cleaned)})."
            )
        return cleaned


class InvalidPhoneNumber(DomainError):
    """Le numéro fourni n'est pas conforme au PNN camerounais."""

    code = "INVALID_PHONE_NUMBER"
