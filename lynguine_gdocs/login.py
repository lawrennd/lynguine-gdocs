"""Interactive Google sign-in for Drive catalogue access."""

from __future__ import annotations

import argparse
import sys

from .oauth import (
    DEFAULT_SCOPES,
    GdocsOAuthError,
    acquire_interactive_grant,
)


def bootstrap(
    *,
    name: str,
    client_id: str,
    client_secret: str,
    scopes: list[str] | None = None,
    acquire=None,
    store=None,
    printer=None,
) -> dict:
    """Browser grant, then ``set_credential``. Returns the stored dict."""
    grant_fn = acquire or _default_acquire
    cred = grant_fn(
        client_id=client_id,
        client_secret=client_secret,
        scopes=list(scopes or DEFAULT_SCOPES),
    )
    if not isinstance(cred, dict) or not cred.get("refresh_token"):
        raise GdocsOAuthError(
            "Google sign-in did not return a refresh token; "
            "use an Installed OAuth client with offline access"
        )
    store_fn = store or _default_store
    # Omit credential_type on set: lynguine's google_oauth validator expects
    # a {"value": ...} wrapper (get path), not the raw mapping set_credential
    # validates. Same pattern as the Sheets user guide.
    store_fn(name, cred, credential_type=None)
    out = printer or _stderr_printer
    out(f"Stored Google OAuth credential {name!r}")
    return cred


def main(argv=None, *, bootstrap_fn=bootstrap) -> int:
    args = _parse_args(argv)
    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    bootstrap_fn(
        name=args.name,
        client_id=args.client_id,
        client_secret=args.client_secret,
        scopes=scopes or None,
    )
    return 0


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lynguine-gdocs-login",
        description=(
            "Sign in to Google Drive with an Installed OAuth client and store "
            "the refresh token via lynguine set_credential. "
            "Register the Google Cloud client yourself; this command does not "
            "ship a client id."
        ),
    )
    parser.add_argument("--name", required=True, help="CIP-0005 credential key")
    parser.add_argument(
        "--client-id",
        required=True,
        help="Google OAuth Installed client id",
    )
    parser.add_argument(
        "--client-secret",
        required=True,
        help="Google OAuth Installed client secret",
    )
    parser.add_argument(
        "--scopes",
        default=",".join(DEFAULT_SCOPES),
        help="Comma-separated OAuth scopes (default Drive readonly)",
    )
    return parser.parse_args(argv)


def _default_acquire(**kwargs):
    return acquire_interactive_grant(**kwargs)


def _default_store(name, value, credential_type=None):
    from lynguine.security import set_credential

    set_credential(name, value, credential_type=credential_type)


def _stderr_printer(message: str) -> None:
    print(message, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
