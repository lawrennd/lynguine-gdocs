"""Google OAuth token refresh for Drive. No vendor SDK in the read path."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import warnings

DEFAULT_SCOPES = (
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
)

_WRITEBACK_WARNED = False


class GdocsOAuthError(RuntimeError):
    """OAuth client or token failure — not a Drive protocol failure."""


def refresh_access_token(cred: dict[str, str]) -> tuple[str, str | None]:
    """Exchange a refresh token for an access token.

    Returns ``(access_token, new_refresh_or_none)``.
    """
    body = urllib.parse.urlencode(
        {
            "client_id": cred["client_id"],
            "client_secret": cred["client_secret"],
            "refresh_token": cred["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        cred["token_uri"],
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise GdocsOAuthError(
            f"Google token refresh failed with HTTP {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        raise GdocsOAuthError("Google token refresh request failed") from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GdocsOAuthError("Google token response was not JSON") from exc
    if not isinstance(data, dict) or not _nonempty_str(data.get("access_token")):
        raise GdocsOAuthError("Google token refresh did not return an access token")
    new_refresh = data.get("refresh_token")
    if not _nonempty_str(new_refresh) or new_refresh == cred["refresh_token"]:
        new_refresh = None
    return data["access_token"], new_refresh


def persist_rotated_refresh_token(
    details: dict | None,
    cred: dict[str, str],
    new_refresh: str,
) -> None:
    """Write a rotated refresh token via CIP-0005. Warn once if persist fails."""
    global _WRITEBACK_WARNED
    cred["refresh_token"] = new_refresh
    key = (details or {}).get("credential")
    if not isinstance(key, str) or not key.strip():
        return
    payload = {
        "client_id": cred["client_id"],
        "client_secret": cred["client_secret"],
        "refresh_token": new_refresh,
        "token_uri": cred["token_uri"],
    }
    try:
        from lynguine.security import set_credential

        set_credential(key.strip(), payload)
    except Exception:
        if not _WRITEBACK_WARNED:
            _WRITEBACK_WARNED = True
            warnings.warn(
                "Google OAuth refresh token rotated but could not be stored; "
                "the new token is kept for this process only",
                UserWarning,
                stacklevel=2,
            )


def acquire_interactive_grant(
    *,
    client_id: str,
    client_secret: str,
    scopes: list[str] | None = None,
    token_uri: str = "https://oauth2.googleapis.com/token",
    auth_uri: str = "https://accounts.google.com/o/oauth2/auth",
) -> dict:
    """Installed-app browser sign-in. Requires the oauth extra."""
    InstalledAppFlow = _load_installed_app_flow()
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": auth_uri,
            "token_uri": token_uri,
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=list(scopes or DEFAULT_SCOPES),
    )
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    refresh = getattr(credentials, "refresh_token", None)
    if not _nonempty_str(refresh):
        raise GdocsOAuthError(
            "Google sign-in did not return a refresh token; "
            "use an Installed OAuth client with offline access"
        )
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh.strip(),
        "token_uri": token_uri,
    }


def _load_installed_app_flow():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise GdocsOAuthError(
            "Interactive Google sign-in requires the oauth extra: "
            "pip install 'lynguine-gdocs[oauth]'"
        ) from exc
    return InstalledAppFlow


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())
