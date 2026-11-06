---
id: "0001"
title: "Google Docs catalogue as a lynguine table"
status: "Implemented"
priority: "High"
created: "2026-11-06"
last_updated: "2026-11-06"
related_tenets: []
stakeholders:
- Application developers (referia and other lynguine flows)
- Operators who keep working documents in Google Docs
tags:
- requirement
- access
- gdocs
- plugins
---

# REQ-0001: Google Docs catalogue as a lynguine table

> Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

A lynguine flow can name `type: gdocs` and receive a DataFrame of Google
Doc **metadata**: one row per Doc, with identity, title, url, modified
time, and owners. Drive is the authoritative catalogue. Doc **bodies**
are out of scope for this requirement.

Lynguine stays thin: this package implements the type. Secrets stay in
CIP-0005 under the existing `google_oauth` kind; YAML names a credential
key, not a token. The type is read-only. Missing credentials and
authorization failures fail clearly.

**Why this matters**: lynguine CIP-0019 / REQ-0010 exists so vendor
stores do not land in `io.py`. Sheets already live in core as
`type: gsheet`. Docs as an inbox/allocation table needs the same plugin
form as Trello cards and mail subjects. Full Doc text remains a
CIP-0013 document reader (a later requirement in this repository).

**Who benefits**: review and allocation flows that want a Docs folder or
Drive query as the working table without exporting to YAML or CSV first.

## Acceptance Criteria

- [x] A flow with `type: gdocs` receives a DataFrame of Doc metadata
- [x] Credentials come from lynguine (`credential_value`) using
      `google_oauth`; tokens are not in YAML
- [x] Doc bodies are not returned as table columns
- [x] `write_data` on `type: gdocs` fails as read-only
- [x] CI tests do not open a network connection or use a live Drive
- [x] The table grain is one row per Google Doc
- [x] Optional folder id and extra Drive query restrict the catalogue
      without inventing a second type name

## Notes

Inbound catalogue only. Editing Docs, commenting, and body extraction
are later requirements if needed.

Google Sheets remain core `type: gsheet`. This requirement must not
register a competing Sheets type.

Zero-plugin path remains valid: export a Docs list to YAML or CSV and
use a builtin `type:`.

## References

- lynguine [CIP-0019](https://github.com/lawrennd/lynguine/blob/main/cip/cip0019.md)
- lynguine [REQ-0010](https://github.com/lawrennd/lynguine/blob/main/requirements/req0010_pluggable-io-types.md)
- [Writing a tabular IO plugin](https://github.com/lawrennd/lynguine/blob/main/docs/getting_started/io_plugins.rst)

## Progress Updates

### 2026-11-06

Requirement created. CIP-0001 reader, mocked tests, login helper, and
README landed. Status Implemented, awaiting a live Drive check before
Validated. Doc body is [REQ-0002](./req0002_gdocs-body.md).
