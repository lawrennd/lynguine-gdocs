"""gdocs reader tests use a fake fetch. No network."""

from email.message import Message
from io import BytesIO
import json
import urllib.error
import urllib.request

import pandas as pd
import pytest

from lynguine.access.io import write_data
from lynguine.access.io_types import ReadOnlyIOTypeError

from lynguine_gdocs.oauth import GdocsOAuthError, refresh_access_token
from lynguine_gdocs.reader import (
    COLUMNS,
    DOC_MIME,
    GdocsAccessError,
    fetch_drive,
    read_gdocs,
)

from .fake_drive import FakeDrive, sample_files

CREDS = {
    "client_id": "id",
    "client_secret": "secret",
    "refresh_token": "1//refresh",
}


def _details(**extra):
    return {"credential_value": dict(CREDS), **extra}


def test_empty_catalogue_has_columns_and_no_rows():
    fake = FakeDrive(files=[])
    df = read_gdocs(_details(), fetch=fake)
    assert list(df.columns) == COLUMNS
    assert len(df) == 0


def test_two_docs_join_owners():
    df = read_gdocs(_details(), fetch=FakeDrive())
    assert list(df.columns) == COLUMNS
    assert list(df["id"]) == ["doc-1", "doc-2"]
    assert df.loc[0, "owners"] == "neil@example.com"
    assert df.loc[1, "owners"] == "Ada; ada@example.com"
    assert bool(df.loc[0, "shared"]) is True
    assert bool(df.loc[1, "starred"]) is True
    assert "body" not in df.columns


def test_folder_query_and_limit():
    fake = FakeDrive()
    read_gdocs(_details(folder="folder-1", query="name contains 'paper'"), fetch=fake)
    q = fake.calls[0][1]["q"]
    assert DOC_MIME in q
    assert "trashed = false" in q
    assert "'folder-1' in parents" in q
    assert "(name contains 'paper')" in q

    limited = read_gdocs(_details(limit=1), fetch=FakeDrive())
    assert list(limited["id"]) == ["doc-1"]


def test_pagination_stops_at_limit():
    pages = [sample_files()[:1], sample_files()[1:]]
    fake = FakeDrive(pages=pages)
    df = read_gdocs(_details(limit=1), fetch=fake)
    assert list(df["id"]) == ["doc-1"]
    assert len(fake.calls) == 1


def test_pagination_continues_without_limit():
    pages = [sample_files()[:1], sample_files()[1:]]
    fake = FakeDrive(pages=pages)
    df = read_gdocs(_details(), fetch=fake)
    assert list(df["id"]) == ["doc-1", "doc-2"]
    assert len(fake.calls) == 2


def test_missing_credential_and_bad_limit():
    with pytest.raises(ValueError, match="credential_value"):
        read_gdocs({"folder": "x"}, fetch=FakeDrive())
    with pytest.raises(ValueError, match="refresh_token"):
        read_gdocs(
            {"credential_value": {"client_id": "id", "client_secret": "s"}},
            fetch=FakeDrive(),
        )
    with pytest.raises(ValueError, match="positive integer"):
        read_gdocs(_details(limit=0), fetch=FakeDrive())


def test_http_401_omits_token(monkeypatch):
    secret = "ya29.SECRET"

    def _urlopen(request, timeout=30):
        raise urllib.error.HTTPError(
            request.full_url,
            401,
            "error",
            Message(),
            BytesIO(b'{"error":"unauthorized"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    with pytest.raises(GdocsAccessError, match="authorization failed") as denied:
        fetch_drive(
            "https://www.googleapis.com/drive/v3/files",
            {"q": "trashed=false"},
            access_token=secret,
        )
    assert secret not in str(denied.value)


def test_token_refresh_http_error(monkeypatch):
    def _urlopen(request, timeout=30):
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "error",
            Message(),
            BytesIO(b'{"error":"invalid_grant"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    with pytest.raises(GdocsOAuthError, match="HTTP 400") as failed:
        refresh_access_token(
            {
                **CREDS,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )
    assert "1//refresh" not in str(failed.value)


def test_token_refresh_success(monkeypatch):
    class _Resp(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _open(request, timeout=30):
        return _Resp(
            json.dumps(
                {"access_token": "ya29.access", "refresh_token": "1//new"}
            ).encode("utf-8")
        )

    monkeypatch.setattr(urllib.request, "urlopen", _open)
    access, new_refresh = refresh_access_token(
        {**CREDS, "token_uri": "https://oauth2.googleapis.com/token"}
    )
    assert access == "ya29.access"
    assert new_refresh == "1//new"


def test_gdocs_write_is_read_only():
    import lynguine_gdocs  # noqa: F401

    with pytest.raises(ReadOnlyIOTypeError, match="read-only"):
        write_data(pd.DataFrame(), {"type": "gdocs", "write": True})
