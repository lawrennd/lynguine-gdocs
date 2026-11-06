"""Google Docs for lynguine: catalogue table and CIP-0013 body reader.

Importing this module registers ``type: gdocs`` (one row per Google Doc)
with ``credential_type="google_oauth"``. lynguine fetches the secret
named by ``credential:``; this package only reads ``credential_value``.

Doc **body** is ``read_gdoc`` / ``gdoc_segment`` (CIP-0002) — a CIP-0013
``Document``, not a catalogue column.
"""

from __future__ import annotations

from lynguine.access.io import register_io_type

from .body import gdoc_segment, read_gdoc
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
    "gdoc_segment",
    "read_gdoc",
    "read_gdocs",
    "register",
]
