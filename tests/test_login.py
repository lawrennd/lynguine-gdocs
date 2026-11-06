from lynguine_gdocs.login import bootstrap, main
from lynguine_gdocs.oauth import GdocsOAuthError
import pytest


def test_bootstrap_stores_google_oauth():
    stored = {}

    def acquire(**kwargs):
        assert kwargs["client_id"] == "id"
        return {
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "1//token",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

    def store(name, value, credential_type=None):
        stored["name"] = name
        stored["value"] = value
        stored["credential_type"] = credential_type

    messages = []
    cred = bootstrap(
        name="my_google",
        client_id="id",
        client_secret="secret",
        acquire=acquire,
        store=store,
        printer=messages.append,
    )
    assert cred["refresh_token"] == "1//token"
    assert stored["name"] == "my_google"
    assert stored["credential_type"] is None
    assert messages == ["Stored Google OAuth credential 'my_google'"]


def test_bootstrap_rejects_missing_refresh():
    with pytest.raises(GdocsOAuthError, match="did not return a refresh token"):
        bootstrap(
            name="x",
            client_id="id",
            client_secret="secret",
            acquire=lambda **k: {"client_id": "id"},
            store=lambda *a, **k: None,
        )


def test_main_passes_args():
    seen = {}

    def fake_bootstrap(**kwargs):
        seen.update(kwargs)

    code = main(
        [
            "--name",
            "my_google",
            "--client-id",
            "cid",
            "--client-secret",
            "csecret",
            "--scopes",
            "https://www.googleapis.com/auth/drive.readonly, https://www.googleapis.com/auth/documents.readonly",
        ],
        bootstrap_fn=fake_bootstrap,
    )
    assert code == 0
    assert seen["name"] == "my_google"
    assert seen["client_id"] == "cid"
    assert seen["client_secret"] == "csecret"
    assert seen["scopes"] == [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/documents.readonly",
    ]


def test_default_store_and_acquire(monkeypatch, capsys):
    from lynguine_gdocs import login as login_mod

    seen = {}

    def fake_set(name, value, credential_type=None):
        seen["name"] = name
        seen["value"] = value
        seen["type"] = credential_type

    monkeypatch.setattr("lynguine.security.set_credential", fake_set)
    login_mod._default_store("k", {"refresh_token": "1//x"}, credential_type=None)
    assert seen["name"] == "k"

    monkeypatch.setattr(
        login_mod,
        "acquire_interactive_grant",
        lambda **k: {"refresh_token": "1//y", **k},
    )
    out = login_mod._default_acquire(client_id="id", client_secret="s")
    assert out["refresh_token"] == "1//y"

    login_mod._stderr_printer("hello")
    assert "hello" in capsys.readouterr().err
