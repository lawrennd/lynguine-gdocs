import pytest

from lynguine_gdocs.credentials import normalize_google_oauth, unwrap_credential


def test_normalize_requires_refresh_token_and_strips():
    assert normalize_google_oauth(
        {
            "client_id": " id ",
            "client_secret": " secret ",
            "refresh_token": " 1//token ",
        }
    ) == {
        "client_id": "id",
        "client_secret": "secret",
        "refresh_token": "1//token",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def test_normalize_custom_token_uri():
    out = normalize_google_oauth(
        {
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "1//token",
            "token_uri": " https://example.test/token ",
        }
    )
    assert out["token_uri"] == "https://example.test/token"


def test_normalize_rejects_non_mapping():
    with pytest.raises(ValueError, match="must be a mapping"):
        normalize_google_oauth("nope")


def test_normalize_names_missing_fields():
    with pytest.raises(ValueError, match="refresh_token"):
        normalize_google_oauth({"client_id": "id", "client_secret": "secret"})


def test_unwrap_value_wrapper():
    raw = {"value": {"client_id": "id", "client_secret": "s", "refresh_token": "r"}}
    assert unwrap_credential(raw)["client_id"] == "id"
    assert unwrap_credential({"client_id": "id"})["client_id"] == "id"
    with pytest.raises(ValueError, match="must be a mapping"):
        unwrap_credential("nope")
