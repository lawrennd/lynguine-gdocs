"""OAuth helper tests. No network."""

import json
import urllib.error
import urllib.request
import warnings
from io import BytesIO

import pytest

from lynguine_gdocs import oauth as oauth_mod
from lynguine_gdocs.oauth import (
    GdocsOAuthError,
    acquire_interactive_grant,
    persist_rotated_refresh_token,
    refresh_access_token,
)


class _Resp(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_refresh_url_error(monkeypatch):
    def _open(request, timeout=30):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", _open)
    with pytest.raises(GdocsOAuthError, match="token refresh request failed"):
        refresh_access_token(
            {
                "client_id": "id",
                "client_secret": "secret",
                "refresh_token": "1//r",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )


def test_refresh_bad_json_and_missing_access(monkeypatch):
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: _Resp(b"not-json")
    )
    with pytest.raises(GdocsOAuthError, match="not JSON"):
        refresh_access_token(
            {
                "client_id": "id",
                "client_secret": "secret",
                "refresh_token": "1//r",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **k: _Resp(json.dumps({"token_type": "Bearer"}).encode()),
    )
    with pytest.raises(GdocsOAuthError, match="did not return an access token"):
        refresh_access_token(
            {
                "client_id": "id",
                "client_secret": "secret",
                "refresh_token": "1//r",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )


def test_refresh_same_refresh_token_is_ignored(monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **k: _Resp(
            json.dumps(
                {"access_token": "ya29.a", "refresh_token": "1//same"}
            ).encode()
        ),
    )
    access, new_refresh = refresh_access_token(
        {
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "1//same",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    assert access == "ya29.a"
    assert new_refresh is None


def test_persist_rotated_refresh_token_success(monkeypatch):
    stored = {}

    def fake_set(key, value, credential_type=None):
        stored["key"] = key
        stored["value"] = value

    monkeypatch.setattr("lynguine.security.set_credential", fake_set)
    cred = {
        "client_id": "id",
        "client_secret": "secret",
        "refresh_token": "1//old",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    persist_rotated_refresh_token({}, cred, "1//new")
    assert cred["refresh_token"] == "1//new"
    assert stored == {}

    persist_rotated_refresh_token(
        {"credential": " my_google "}, cred, "1//rotated"
    )
    assert stored["key"] == "my_google"
    assert stored["value"]["refresh_token"] == "1//rotated"


def test_persist_rotated_refresh_token_warns_once(monkeypatch):
    oauth_mod._WRITEBACK_WARNED = False
    cred = {
        "client_id": "id",
        "client_secret": "secret",
        "refresh_token": "1//old",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    def boom(*args, **kwargs):
        raise RuntimeError("no store")

    monkeypatch.setattr("lynguine.security.set_credential", boom)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        persist_rotated_refresh_token(
            {"credential": "my_google"}, cred, "1//new"
        )
        persist_rotated_refresh_token(
            {"credential": "my_google"}, cred, "1//newer"
        )
    assert len(caught) == 1
    assert "could not be stored" in str(caught[0].message)


def test_acquire_interactive_grant_success(monkeypatch):
    class FakeCreds:
        refresh_token = " 1//from-browser "

    class FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            assert "installed" in config
            return cls()

        def run_local_server(self, **kwargs):
            assert kwargs.get("access_type") == "offline"
            return FakeCreds()

    monkeypatch.setattr(oauth_mod, "_load_installed_app_flow", lambda: FakeFlow)
    out = acquire_interactive_grant(client_id="id", client_secret="secret")
    assert out["refresh_token"] == "1//from-browser"


def test_acquire_interactive_grant_requires_refresh(monkeypatch):
    class FakeCreds:
        refresh_token = None

    class FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            return cls()

        def run_local_server(self, **kwargs):
            return FakeCreds()

    monkeypatch.setattr(oauth_mod, "_load_installed_app_flow", lambda: FakeFlow)
    with pytest.raises(GdocsOAuthError, match="did not return a refresh token"):
        acquire_interactive_grant(client_id="id", client_secret="secret")


def test_load_installed_app_flow_missing_extra(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "google_auth_oauthlib.flow" or name == "google_auth_oauthlib":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(GdocsOAuthError, match="oauth extra"):
        oauth_mod._load_installed_app_flow()
