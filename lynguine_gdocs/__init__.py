"""Google Docs catalogue as a lynguine IO type.

Importing this module registers ``type: gdocs`` (one row per Google Doc)
with ``credential_type="google_oauth"``. lynguine fetches the secret
named by ``credential:``; this package only reads ``credential_value``.

Full Doc body text is a later CIP-0013 reader, not this table type.
"""

from __future__ import annotations

from lynguine.access.io import register_io_type

from .oauth import GdocsOAuthError
from .reader import GdocsAccessError, read_gdocs

register_io_type(
    "gdocs",
    read=read_gdocs,
    credential_type="google_oauth",
)


def register():
    """Entry-point hook. Import already registers the type."""
    from lynguine.access.io_types import get_io_type

    return get_io_type("gdocs")


__all__ = [
    "GdocsAccessError",
    "GdocsOAuthError",
    "read_gdocs",
    "register",
]
