"""Read Google Docs catalogue metadata into a DataFrame.

Drive is the store for the list. This module does not fetch Doc bodies
and does not write back.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, NoReturn

import pandas as pd

from .credentials import normalize_google_oauth, unwrap_credential
from .oauth import persist_rotated_refresh_token, refresh_access_token

DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
DOC_MIME = "application/vnd.google-apps.document"
FILE_FIELDS = (
    "nextPageToken,files(id,name,webViewLink,modifiedTime,createdTime,"
    "owners(displayName,emailAddress),shared,starred)"
)
COLUMNS = [
    "id",
    "name",
    "url",
    "modified",
    "created",
    "owners",
    "shared",
    "starred",
]
PAGE_SIZE = 100


class GdocsAccessError(RuntimeError):
    """Drive HTTP or protocol failure (not a YAML contract error)."""


def read_gdocs(
    details: dict,
    *,
    fetch: Callable[[str, dict[str, str]], object] | None = None,
) -> pd.DataFrame:
    """Read Google Docs metadata from Drive.

    Required YAML:

    * ``credential:`` — CIP-0005 key (lynguine binds ``credential_value``)

    Optional: ``folder`` (Drive folder id), ``query`` (extra Drive ``q``
    clause ANDed with the Docs filter), ``limit`` (positive int).
    """
    cred = _credential(details)
    folder = _folder(details)
    extra_query = _query(details)
    limit = _limit(details)
    drive_query = _drive_query(folder=folder, extra=extra_query)
    do_fetch = fetch if fetch is not None else _authorized_fetch(details, cred)

    rows: list[dict] = []
    page_token: str | None = None
    while True:
        params: dict[str, str] = {
            "q": drive_query,
            "fields": FILE_FIELDS,
            "pageSize": str(PAGE_SIZE),
            "spaces": "drive",
            "corpora": "user",
        }
        if page_token:
            params["pageToken"] = page_token
        payload = do_fetch(DRIVE_FILES, params)
        files, page_token = _parse_list(payload)
        for item in files:
            rows.append(_row_from_file(item))
            if limit is not None and len(rows) >= limit:
                return pd.DataFrame(rows[:limit], columns=COLUMNS)
        if not page_token:
            break
    return pd.DataFrame(rows, columns=COLUMNS)


def fetch_drive(
    url: str,
    params: dict[str, str],
    *,
    access_token: str,
) -> object:
    """GET *url* with *params* and a Bearer token. Do not log the token."""
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        method="GET",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = _http_error_detail(exc)
        _raise_http(exc.code, detail=detail)
        raise
    except urllib.error.URLError as exc:
        raise GdocsAccessError("Google Drive request failed") from exc
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GdocsAccessError("Google Drive response was not JSON") from exc


def _authorized_fetch(details: dict, cred: dict[str, str]):
    access_token, new_refresh = refresh_access_token(cred)
    if new_refresh:
        persist_rotated_refresh_token(details, cred, new_refresh)

    def _fetch(url: str, params: dict[str, str]) -> object:
        return fetch_drive(url, params, access_token=access_token)

    return _fetch


def _raise_http(status: int, *, detail: str | None = None) -> NoReturn:
    suffix = f": {detail}" if detail else ""
    if status in (401, 403):
        raise GdocsAccessError(f"Google Drive authorization failed{suffix}")
    if status == 404:
        raise GdocsAccessError(f"Google Drive resource not found{suffix}")
    if status == 429:
        raise GdocsAccessError(f"Google Drive rate-limited{suffix}")
    raise GdocsAccessError(f"Google Drive HTTP {status}{suffix}")


def _http_error_detail(exc: urllib.error.HTTPError) -> str | None:
    """Return a short Google error message; never include request auth headers."""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict):
        message = err.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        errors = err.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                reason = first.get("reason")
                if isinstance(reason, str) and reason.strip():
                    return reason.strip()
    if isinstance(err, str) and err.strip():
        return err.strip()
    return None


def _credential(details: dict) -> dict[str, str]:
    raw = details.get("credential_value")
    if raw is None:
        raise ValueError("gdocs read expected credential_value from lynguine")
    try:
        return normalize_google_oauth(unwrap_credential(raw))
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _folder(details: dict) -> str | None:
    if "folder" not in details or details["folder"] is None:
        return None
    folder = details["folder"]
    if not isinstance(folder, str) or not folder.strip():
        raise ValueError('Type "gdocs" folder: must be a Drive folder id')
    return folder.strip()


def _query(details: dict) -> str | None:
    if "query" not in details or details["query"] is None:
        return None
    query = details["query"]
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Type "gdocs" query: must be a non-empty Drive q clause')
    return query.strip()


def _limit(details: dict) -> int | None:
    if "limit" not in details or details["limit"] is None:
        return None
    limit = details["limit"]
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError('Type "gdocs" limit: must be a positive integer')
    return limit


def _drive_query(*, folder: str | None, extra: str | None) -> str:
    parts = [f"mimeType = '{DOC_MIME}'", "trashed = false"]
    if folder is not None:
        parts.append(f"'{folder}' in parents")
    if extra is not None:
        parts.append(f"({extra})")
    return " and ".join(parts)


def _parse_list(payload: object) -> tuple[list, str | None]:
    if not isinstance(payload, dict):
        raise GdocsAccessError("Google Drive files response was not an object")
    files = payload.get("files", [])
    if not isinstance(files, list):
        raise GdocsAccessError("Google Drive files response was not a list")
    token = payload.get("nextPageToken")
    if token is not None and not isinstance(token, str):
        raise GdocsAccessError("Google Drive nextPageToken was not a string")
    if isinstance(token, str) and not token:
        token = None
    return files, token


def _row_from_file(item: object) -> dict:
    if not isinstance(item, dict):
        raise GdocsAccessError(
            "Google Drive files response was not a list of files"
        )
    return {
        "id": _text(item.get("id")),
        "name": _text(item.get("name")),
        "url": _text(item.get("webViewLink")),
        "modified": _text(item.get("modifiedTime")),
        "created": _text(item.get("createdTime")),
        "owners": _owners(item.get("owners")),
        "shared": bool(item.get("shared")),
        "starred": bool(item.get("starred")),
    }


def _owners(raw) -> str:
    if not isinstance(raw, list):
        return ""
    names: list[str] = []
    for owner in raw:
        if not isinstance(owner, dict):
            continue
        email = owner.get("emailAddress")
        if isinstance(email, str) and email.strip():
            names.append(email.strip())
            continue
        display = owner.get("displayName")
        if isinstance(display, str) and display.strip():
            names.append(display.strip())
    return "; ".join(names)


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)
