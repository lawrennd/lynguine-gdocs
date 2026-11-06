---
id: "0002"
title: "Google Docs body as a document reader"
status: "Implemented"
priority: "Medium"
created: "2026-11-06"
last_updated: "2026-11-06"
related_tenets: []
stakeholders:
- Application developers who need Doc text in review flows
tags:
- requirement
- access
- gdocs
- documents
---

# REQ-0002: Google Docs body as a document reader

> Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

An operator can fetch the **body** of a Google Doc (by id) into lynguine's
document model so CIP-0013 strategies can segment it. This is not a
DataFrame of paragraphs. The catalogue in REQ-0001 stays metadata-only.

Credentials continue to use `google_oauth`. Body fetch may need Docs API
scopes in addition to Drive readonly.

## Acceptance Criteria

- [x] A Doc id yields document text (or units) without putting the full
      body on every catalogue row by default
- [x] Credentials stay in CIP-0005; secrets are not in YAML
- [x] CI tests do not call live Google APIs

## Notes

Depends on REQ-0001 for auth bootstrap patterns. Implemented by
[CIP-0002](../cip/cip0002.md). Registration of `reader: gdocs` inside
lynguine `document_segment` is a follow-on core change.

## Progress Updates

### 2026-11-06

Requirement Proposed. Catalogue (REQ-0001) ships first.

### 2026-11-06

CIP-0002 implements `read_gdoc` / `gdoc_segment`. Marked Implemented.
