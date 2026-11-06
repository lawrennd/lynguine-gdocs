"""Google Doc body → CIP-0013 Document (not a catalogue column)."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from lynguine.access.documents.model import Block, Document, Page
from lynguine.access.documents.pdf import classify_text_layer
from lynguine.access.documents.segment import segment_document

from .credentials import normalize_google_oauth, unwrap_credential
from .reader import GdocsAccessError, _authorized_fetch

DOCS_GET = "https://docs.googleapis.com/v1/documents/{doc_id}"

_HEADING_LEVEL = {
    "TITLE": 1,
    "SUBTITLE": 2,
    "HEADING_1": 1,
    "HEADING_2": 2,
    "HEADING_3": 3,
    "HEADING_4": 4,
    "HEADING_5": 5,
    "HEADING_6": 6,
}


def read_gdoc(
    doc_id: str,
    details: dict,
    *,
    fetch: Callable[[str, dict[str, str]], object] | None = None,
) -> Document:
    """Fetch one Google Doc and return a CIP-0013 :class:`Document`.

    *details* must include ``credential_value`` (same binding as
    ``type: gdocs``). Inject *fetch* in tests; production uses Docs API
    ``documents.get`` after OAuth refresh.
    """
    doc_id = _doc_id(doc_id)
    cred = _credential(details)
    do_fetch = fetch if fetch is not None else _authorized_fetch(details, cred)
    payload = do_fetch(DOCS_GET.format(doc_id=doc_id), {})
    return document_from_docs_payload(payload, doc_id=doc_id)


def gdoc_segment(
    doc_id: str,
    details: dict,
    *,
    strategy: str = "auto",
    aspect: str = "body_chunks",
    on_sparse_text: str = "error",
    fetch: Callable[[str, dict[str, str]], object] | None = None,
    **strategy_params: Any,
) -> list[dict[str, Any]]:
    """Load a Doc body and return CIP-0013 unit dicts."""
    document = read_gdoc(doc_id, details, fetch=fetch)
    units = segment_document(
        document,
        strategy=strategy,
        aspect=aspect,
        on_sparse_text=on_sparse_text,  # type: ignore[arg-type]
        **strategy_params,
    )
    return [u.to_dict() for u in units]


def document_from_docs_payload(payload: object, *, doc_id: str) -> Document:
    """Map a Docs API ``documents.get`` JSON object to a :class:`Document`."""
    if not isinstance(payload, dict):
        raise GdocsAccessError("Google Docs response was not an object")
    body = payload.get("body")
    if body is not None and not isinstance(body, dict):
        raise GdocsAccessError("Google Docs body was not an object")
    content = (body or {}).get("content", [])
    if content is not None and not isinstance(content, list):
        raise GdocsAccessError("Google Docs body content was not a list")

    lines = list(_content_lines(content or []))
    blocks = [
        Block(
            page_index=0,
            block_index=i,
            x0=0.0,
            y0=float(i),
            x1=1.0,
            y1=float(i) + 1.0,
            text=line,
            block_type="text",
            word_count=len(line.split()),
        )
        for i, line in enumerate(lines)
    ]
    text = "\n".join(lines)
    total_words = len(text.split()) if text.strip() else 0
    text_layer, words_per_page = classify_text_layer(total_words, page_count=1)
    page = Page(
        index=0,
        width=1.0,
        height=float(max(len(blocks), 1)),
        text=text,
        word_count=total_words,
        blocks=tuple(blocks),
    )
    title = payload.get("title")
    revision = payload.get("revisionId")
    return Document(
        path=f"gdocs:{doc_id}",
        reader="gdocs",
        page_count=1,
        total_words=total_words,
        words_per_page=words_per_page,
        text_layer=text_layer,
        pages=(page,),
        metadata={
            "doc_id": doc_id,
            "title": title if isinstance(title, str) else "",
            "revision_id": revision if isinstance(revision, str) else "",
            "line_count": len(blocks),
        },
    )


def _content_lines(content: Iterable[object]) -> list[str]:
    lines: list[str] = []
    for element in content:
        if not isinstance(element, dict):
            continue
        if "paragraph" in element:
            line = _paragraph_line(element["paragraph"])
            if line:
                lines.append(line)
            continue
        if "table" in element:
            lines.extend(_table_lines(element["table"]))
    return lines


def _table_lines(table: object) -> list[str]:
    if not isinstance(table, dict):
        return []
    lines: list[str] = []
    for row in table.get("tableRows") or []:
        if not isinstance(row, dict):
            continue
        for cell in row.get("tableCells") or []:
            if not isinstance(cell, dict):
                continue
            cell_content = cell.get("content") or []
            if isinstance(cell_content, list):
                lines.extend(_content_lines(cell_content))
    return lines


def _paragraph_line(paragraph: object) -> str | None:
    if not isinstance(paragraph, dict):
        return None
    style = paragraph.get("paragraphStyle") or {}
    named = ""
    if isinstance(style, dict):
        raw_named = style.get("namedStyleType")
        if isinstance(raw_named, str):
            named = raw_named
    level = _HEADING_LEVEL.get(named, 0)
    parts: list[str] = []
    for element in paragraph.get("elements") or []:
        if not isinstance(element, dict):
            continue
        run = element.get("textRun")
        if not isinstance(run, dict):
            continue
        content = run.get("content")
        if isinstance(content, str):
            parts.append(content)
    text = "".join(parts).replace("\xa0", " ").rstrip("\n").strip()
    if not text:
        return None
    if level > 0:
        return f"{'#' * level} {text}"
    return text


def _doc_id(doc_id: str) -> str:
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise ValueError("gdocs body expected a non-empty Google Doc id")
    return doc_id.strip()


def _credential(details: dict) -> dict[str, str]:
    raw = details.get("credential_value")
    if raw is None:
        raise ValueError("gdocs body expected credential_value from lynguine")
    try:
        return normalize_google_oauth(unwrap_credential(raw))
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
