"""Live Drive smoke test for type: gdocs. Secrets stay in Keychain / CIP-0005."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request

from lynguine.security import set_credential

from lynguine_gdocs.reader import COLUMNS, read_gdocs

REDIRECT = "https://google.github.io/gmail-oauth2-tools/html/oauth2.dance.html"
TOKEN_URI = "https://oauth2.googleapis.com/token"
CRED_NAME = "gdocs_smoke"
KEYCHAIN_SERVICE = "lynguine-gdocs-refresh"
KEYCHAIN_ACCOUNT = "gdocs_smoke"


def keychain(service: str, account: str) -> str:
    return subprocess.check_output(
        [
            "security",
            "find-generic-password",
            "-s",
            service,
            "-a",
            account,
            "-w",
        ],
        text=True,
    ).strip()


def keychain_set(service: str, account: str, value: str) -> None:
    subprocess.run(
        ["security", "delete-generic-password", "-s", service, "-a", account],
        check=False,
        capture_output=True,
    )
    subprocess.check_call(
        [
            "security",
            "add-generic-password",
            "-s",
            service,
            "-a",
            account,
            "-w",
            value,
        ]
    )


def oauth_payload(refresh_token: str) -> dict:
    return {
        "client_id": keychain("offlineimap-google", "client_id"),
        "client_secret": keychain("offlineimap-google", "client_secret"),
        "refresh_token": refresh_token.strip(),
        "token_uri": TOKEN_URI,
    }


def exchange_code(code: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "code": code.strip(),
            "client_id": keychain("offlineimap-google", "client_id"),
            "client_secret": keychain("offlineimap-google", "client_secret"),
            "redirect_uri": REDIRECT,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URI,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    refresh = data.get("refresh_token")
    if not isinstance(refresh, str) or not refresh.strip():
        raise SystemExit(
            "No refresh_token in response. Revoke prior grants and retry with prompt=consent."
        )
    payload = oauth_payload(refresh)
    # Persist for later --use-stored runs (env provider is process-local).
    keychain_set(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, refresh.strip())
    # Also try CIP-0005 for the current process (Sheets user-guide style).
    set_credential(CRED_NAME, payload)
    print(f"Stored Keychain {KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT}", file=sys.stderr)
    print(f"Stored CIP-0005 credential {CRED_NAME!r} (this process)", file=sys.stderr)
    return payload


def load_stored() -> dict:
    try:
        refresh = keychain(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"No Keychain item {KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT}; pass --code first"
        ) from exc
    if not refresh.startswith("1//"):
        raise SystemExit(
            "Stored refresh token does not look like a Google refresh token (expected 1//…)"
        )
    return oauth_payload(refresh)


def run_catalogue(cred: dict, *, limit: int, folder: str | None) -> None:
    details = {
        "credential_value": cred,
        "credential": CRED_NAME,
        "limit": limit,
    }
    if folder:
        details["folder"] = folder
    df = read_gdocs(details)
    assert list(df.columns) == COLUMNS
    print(f"rows={len(df)} columns={list(df.columns)}")
    if len(df):
        shown = df[["id", "name", "modified", "owners"]].head(min(limit, 10))
        print(shown.to_string(index=False))
    else:
        print("(no Google Docs matched the default catalogue query)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", help="OAuth authorization code from the dance page")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--folder", default=None)
    parser.add_argument(
        "--use-stored",
        action="store_true",
        help=f"Use Keychain refresh token {KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT}",
    )
    args = parser.parse_args(argv)

    if args.use_stored:
        cred = load_stored()
    elif args.code:
        cred = exchange_code(args.code)
    else:
        parser.error("pass --code CODE or --use-stored")

    run_catalogue(cred, limit=args.limit, folder=args.folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
