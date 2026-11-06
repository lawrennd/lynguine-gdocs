"""Normalize google_oauth payloads for Drive catalogue reads.

lynguine already validates ``google_oauth`` (client_id + client_secret).
This package additionally requires a refresh token for user-delegated
Drive access. Do not register a second credential kind.
"""

from __future__ import annotations

REQUIRED = ("client_id", "client_secret", "refresh_token")
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


def normalize_google_oauth(value: dict) -> dict[str, str]:
    """Return stripped OAuth fields. Raise if a required field is missing."""
    if not isinstance(value, dict):
        raise ValueError("Google OAuth credential_value must be a mapping")
    missing = [key for key in REQUIRED if not _nonempty(value, key)]
    if missing:
        raise ValueError(
            "Google OAuth credential_value missing " + ", ".join(missing)
        )
    out = {key: value[key].strip() for key in REQUIRED}
    if _nonempty(value, "token_uri"):
        out["token_uri"] = value["token_uri"].strip()
    else:
        out["token_uri"] = DEFAULT_TOKEN_URI
    return out


def unwrap_credential(credential) -> dict:
    """Accept a raw mapping or CIP-0005 ``{"value": {...}}`` wrapper."""
    if isinstance(credential, dict) and "value" in credential and isinstance(
        credential.get("value"), dict
    ):
        return credential["value"]
    if isinstance(credential, dict):
        return credential
    raise ValueError("Google OAuth credential_value must be a mapping")


def _nonempty(value: dict, key: str) -> bool:
    item = value.get(key)
    return isinstance(item, str) and bool(item.strip())
