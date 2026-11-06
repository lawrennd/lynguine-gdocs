"""The package must declare type gdocs and credential_type google_oauth."""

from lynguine.access.io_types import get_io_type


def test_import_registers_gdocs():
    import lynguine_gdocs  # noqa: F401

    spec = get_io_type("gdocs")
    assert spec is not None
    assert spec.name == "gdocs"
    assert spec.credential_type == "google_oauth"
    assert spec.write is None
    assert spec.read is lynguine_gdocs.read_gdocs


def test_register_returns_the_gdocs_type():
    import lynguine_gdocs

    spec = lynguine_gdocs.register()
    assert spec is get_io_type("gdocs")
    assert spec.read is lynguine_gdocs.read_gdocs
