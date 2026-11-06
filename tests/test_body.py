"""Google Doc body → CIP-0013 Document. No network."""

import pytest

from lynguine.access.documents.model import TextLayer
from lynguine.access.documents.errors import SparseTextLayerError

from lynguine_gdocs.body import gdoc_segment, read_gdoc
from lynguine_gdocs.reader import GdocsAccessError

from .fake_docs import FakeDocs, empty_docs_payload, sample_docs_payload

CREDS = {
    "client_id": "id",
    "client_secret": "secret",
    "refresh_token": "1//refresh",
}


def _details(**extra):
    return {"credential_value": dict(CREDS), **extra}


def test_read_gdoc_builds_document_with_headings_and_table():
    fake = FakeDocs()
    doc = read_gdoc("doc-1", _details(), fetch=fake)
    assert doc.path == "gdocs:doc-1"
    assert doc.reader == "gdocs"
    assert doc.page_count == 1
    assert doc.text_layer == TextLayer.PRESENT
    assert doc.metadata["title"] == "Sample paper"
    assert doc.metadata["revision_id"] == "rev-1"
    assert doc.metadata["doc_id"] == "doc-1"
    texts = [b.text for b in doc.pages[0].blocks]
    assert texts[0] == "# Introduction"
    assert texts[1].startswith("First paragraph with enough words")
    assert "Cell A" in texts
    assert "Cell B" in texts
    assert texts[-1] == "# Appendix"
    assert fake.calls[0][0].endswith("/documents/doc-1")


def test_empty_doc_is_absent_text_layer():
    doc = read_gdoc("empty", _details(), fetch=FakeDocs(payload=empty_docs_payload()))
    assert doc.total_words == 0
    assert doc.text_layer == TextLayer.ABSENT
    assert doc.pages[0].blocks == ()


def test_gdoc_segment_returns_unit_dicts():
    units = gdoc_segment(
        "doc-1",
        _details(),
        strategy="pub_dialogue.v1",
        aspect="body_chunks",
        fetch=FakeDocs(),
        min_chunk_words=5,
        min_chunk_chars=10,
        sentence_fallback_min_paragraphs=1,
    )
    assert units
    assert all("text" in u for u in units)
    assert all(u.get("segment_strategy") == "pub_dialogue.v1" for u in units)
    joined = " ".join(u["text"] for u in units)
    assert "paragraph" in joined.lower() or "Introduction" in joined


def test_empty_doc_segment_errors_by_default():
    with pytest.raises(SparseTextLayerError):
        gdoc_segment(
            "empty",
            _details(),
            strategy="pub_dialogue.v1",
            fetch=FakeDocs(payload=empty_docs_payload()),
        )


def test_missing_credential_and_bad_id():
    with pytest.raises(ValueError, match="credential_value"):
        read_gdoc("doc-1", {}, fetch=FakeDocs())
    with pytest.raises(ValueError, match="Doc id"):
        read_gdoc("  ", _details(), fetch=FakeDocs())


def test_payload_protocol_errors():
    with pytest.raises(GdocsAccessError, match="not an object"):
        read_gdoc("doc-1", _details(), fetch=lambda url, params: ["nope"])
    with pytest.raises(GdocsAccessError, match="body was not an object"):
        read_gdoc(
            "doc-1",
            _details(),
            fetch=lambda url, params: {"title": "x", "body": "bad"},
        )
    with pytest.raises(GdocsAccessError, match="content was not a list"):
        read_gdoc(
            "doc-1",
            _details(),
            fetch=lambda url, params: {"body": {"content": "bad"}},
        )


def test_subtitle_heading_and_skips():
    payload = sample_docs_payload()
    payload["body"]["content"].insert(
        0,
        {
            "sectionBreak": {},
        },
    )
    payload["body"]["content"].insert(
        1,
        {
            "paragraph": {
                "paragraphStyle": {"namedStyleType": "SUBTITLE"},
                "elements": [{"textRun": {"content": "A subtitle\n"}}],
            }
        },
    )
    payload["body"]["content"].append(
        {
            "paragraph": {
                "paragraphStyle": "bad",
                "elements": ["skip", {"textRun": "bad"}, {"textRun": {"content": 1}}],
            }
        }
    )
    payload["body"]["content"].append(
        {
            "table": {
                "tableRows": [
                    "skip-row",
                    {"tableCells": ["skip-cell", {"content": "bad"}, {"content": []}]},
                ]
            }
        }
    )
    doc = read_gdoc("doc-1", _details(), fetch=FakeDocs(payload=payload))
    assert doc.pages[0].blocks[0].text == "## A subtitle"


def test_bad_credential_normalize():
    with pytest.raises(ValueError, match="refresh_token"):
        read_gdoc(
            "doc-1",
            {"credential_value": {"client_id": "id", "client_secret": "s"}},
            fetch=FakeDocs(),
        )
