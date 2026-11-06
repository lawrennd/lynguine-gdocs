"""Reader error-path and authorized-fetch tests. No network."""

import json
import urllib.error
import urllib.request
from email.message import Message
from io import BytesIO

import pytest

from lynguine_gdocs.reader import (
    GdocsAccessError,
    fetch_drive,
    read_gdocs,
)

from .fake_drive import FakeDrive, sample_files
from .test_read import CREDS, _details


class _Resp(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_http_403_includes_google_message(monkeypatch):
    body = json.dumps(
        {"error": {"message": "Google Drive API has not been used"}}
    ).encode()

    def _urlopen(request, timeout=30):
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            Message(),
            BytesIO(body),
        )

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    with pytest.raises(GdocsAccessError, match="has not been used"):
        fetch_drive(
            "https://www.googleapis.com/drive/v3/files",
            {"q": "trashed=false"},
            access_token="ya29.SECRET",
        )


def test_http_404_429_and_other(monkeypatch):
    def _boom(code):
        def _urlopen(request, timeout=30):
            raise urllib.error.HTTPError(
                request.full_url,
                code,
                "error",
                Message(),
                BytesIO(b'{"error":{"errors":[{"reason":"rateLimitExceeded"}]}}'),
            )

        return _urlopen

    monkeypatch.setattr(urllib.request, "urlopen", _boom(404))
    with pytest.raises(GdocsAccessError, match="not found"):
        fetch_drive("https://example.test/files", {}, access_token="t")

    monkeypatch.setattr(urllib.request, "urlopen", _boom(429))
    with pytest.raises(GdocsAccessError, match="rate-limited"):
        fetch_drive("https://example.test/files", {}, access_token="t")

    monkeypatch.setattr(urllib.request, "urlopen", _boom(500))
    with pytest.raises(GdocsAccessError, match="HTTP 500"):
        fetch_drive("https://example.test/files", {}, access_token="t")


def test_fetch_drive_url_error_and_bad_json(monkeypatch):
    def _url_error(request, timeout=30):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", _url_error)
    with pytest.raises(GdocsAccessError, match="request failed"):
        fetch_drive("https://example.test/files", {}, access_token="t")

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: _Resp(b"not-json")
    )
    with pytest.raises(GdocsAccessError, match="not JSON"):
        fetch_drive("https://example.test/files", {}, access_token="t")


def test_fetch_drive_success(monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **k: _Resp(json.dumps({"files": []}).encode()),
    )
    assert fetch_drive(
        "https://www.googleapis.com/drive/v3/files",
        {"q": "trashed=false"},
        access_token="t",
    ) == {"files": []}


def test_authorized_fetch_persists_rotated_token(monkeypatch):
    seen = {}

    def fake_refresh(cred):
        return "ya29.access", "1//rotated"

    def fake_persist(details, cred, new_refresh):
        seen["details"] = details
        seen["refresh"] = new_refresh
        cred["refresh_token"] = new_refresh

    monkeypatch.setattr("lynguine_gdocs.reader.refresh_access_token", fake_refresh)
    monkeypatch.setattr(
        "lynguine_gdocs.reader.persist_rotated_refresh_token", fake_persist
    )
    monkeypatch.setattr(
        "lynguine_gdocs.reader.fetch_drive",
        lambda url, params, access_token: {"files": sample_files()[:1]},
    )
    df = read_gdocs(
        {
            "credential_value": dict(CREDS),
            "credential": "gdocs_smoke",
            "limit": 1,
        }
    )
    assert list(df["id"]) == ["doc-1"]
    assert seen["refresh"] == "1//rotated"
    assert seen["details"]["credential"] == "gdocs_smoke"


def test_parse_list_and_row_errors():
    with pytest.raises(GdocsAccessError, match="not an object"):
        read_gdocs(_details(), fetch=lambda url, params: ["nope"])

    with pytest.raises(GdocsAccessError, match="not a list"):
        read_gdocs(_details(), fetch=lambda url, params: {"files": "x"})

    with pytest.raises(GdocsAccessError, match="nextPageToken"):
        read_gdocs(_details(), fetch=lambda url, params: {"files": [], "nextPageToken": 1})

    with pytest.raises(GdocsAccessError, match="list of files"):
        read_gdocs(_details(), fetch=lambda url, params: {"files": ["x"]})


def test_empty_page_token_and_owner_fallbacks():
    def fetch(url, params):
        return {
            "files": [
                {
                    "id": 123,
                    "name": None,
                    "webViewLink": None,
                    "modifiedTime": None,
                    "createdTime": None,
                    "owners": "bad",
                    "shared": False,
                    "starred": False,
                },
                {
                    "id": "doc-x",
                    "name": "X",
                    "webViewLink": "u",
                    "modifiedTime": "m",
                    "createdTime": "c",
                    "owners": [{"displayName": "Only Name"}, "skip", {}],
                    "shared": False,
                    "starred": False,
                },
            ],
            "nextPageToken": "",
        }

    df = read_gdocs(_details(), fetch=fetch)
    assert df.loc[0, "id"] == "123"
    assert df.loc[0, "owners"] == ""
    assert df.loc[1, "owners"] == "Only Name"


def test_bad_folder_and_query():
    with pytest.raises(ValueError, match="folder"):
        read_gdocs(_details(folder=" "), fetch=FakeDrive())
    with pytest.raises(ValueError, match="query"):
        read_gdocs(_details(query=""), fetch=FakeDrive())


def test_http_error_detail_fallbacks():
    from lynguine_gdocs.reader import _http_error_detail

    class FakeHTTP(urllib.error.HTTPError):
        def __init__(self, payload):
            urllib.error.HTTPError.__init__(
                self, "https://example.test", 403, "x", Message(), BytesIO(payload)
            )

        def read(self):
            raise OSError("boom")

    assert _http_error_detail(FakeHTTP(b"{}")) is None

    err = urllib.error.HTTPError(
        "https://example.test",
        403,
        "x",
        Message(),
        BytesIO(b"not-json"),
    )
    assert _http_error_detail(err) is None

    err = urllib.error.HTTPError(
        "https://example.test",
        403,
        "x",
        Message(),
        BytesIO(b'{"error":"plain"}'),
    )
    assert _http_error_detail(err) == "plain"

    err = urllib.error.HTTPError(
        "https://example.test",
        403,
        "x",
        Message(),
        BytesIO(
            b'{"error":{"errors":[{"reason":"dailyLimitExceeded"}]}}'
        ),
    )
    assert _http_error_detail(err) == "dailyLimitExceeded"

    err = urllib.error.HTTPError(
        "https://example.test",
        403,
        "x",
        Message(),
        BytesIO(b'{"error":{"errors":[]}}'),
    )
    assert _http_error_detail(err) is None
