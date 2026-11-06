# lynguine-gdocs

Google Docs for lynguine:

* **Catalogue** — `type: gdocs` (CIP-0001). One row per Doc; metadata
  only; read-only.
* **Body** — `read_gdoc` / `gdoc_segment` (CIP-0002). One Doc id →
  CIP-0013 `Document` / segment units. Not a catalogue column.

Point at the plugin form in lynguine:

https://github.com/lawrennd/lynguine/blob/main/docs/getting_started/io_plugins.rst

Google Sheets stay core `type: gsheet`. Do not register a second Sheets
type in this package.

## Authorisation

This package **declares** `credential_type="google_oauth"`. It does not
open the credential store. lynguine (CIP-0005) fetches the secret named
by `credential:` and passes it as `credential_value`.

Reuse the existing `google_oauth` kind (same as Sheets). Store
`{client_id, client_secret, refresh_token}` under a CIP-0005 key. Do not
put tokens in YAML.

Enable the **Google Drive API** and the **Google Docs API** on a Google
Cloud project. Create a **Desktop / Installed** OAuth client. Add the
Google account as a test user while the consent screen is in Testing.

Default login scopes:

* `https://www.googleapis.com/auth/drive.readonly`
* `https://www.googleapis.com/auth/documents.readonly`

```bash
pip install 'lynguine-gdocs[oauth]'

python -m lynguine_gdocs.login --name my_google \
  --client-id '....apps.googleusercontent.com' \
  --client-secret '...'
```

Re-run login after upgrading past CIP-0002 so the refresh token includes
`documents.readonly`. Encrypted-file storage needs a master key
(lynguine CIP-001A / OS keyring) and writes under
`~/.lynguine/credentials/`.

A Testing OAuth app expires refresh tokens after 7 days. Re-run login
when Drive or Docs returns authorization failures after that window.

## Catalogue YAML

```yaml
plugins:
  - lynguine_gdocs

allocation:
  type: gdocs
  index: id
  credential: my_google
```

Optional keys: `folder` (Drive folder id — not the folder name),
`query` (extra Drive `q` clause ANDed with the Docs filter), `limit`
(first N Docs in Drive's order). `index:` is lynguine `finalize_data`;
use `id`.

Each row is one Google Doc: `id`, `name`, `url`, `modified`, `created`,
`owners`, `shared`, `starred`. `owners` are email addresses (or display
names) joined with `"; "`. Body text is not a column.

Zero matches is an empty frame with those columns. Write-back is out of
scope.

## Doc body (CIP-0013)

Fetch one Doc by id into lynguine's document model, then segment:

```python
from lynguine_gdocs import read_gdoc, gdoc_segment

doc = read_gdoc(doc_id, {"credential_value": cred})
units = gdoc_segment(
    doc_id,
    {"credential_value": cred},
    strategy="pub_dialogue.v1",
    aspect="body_chunks",
)
```

Headings from Docs styles (`TITLE`, `HEADING_n`) become markdown `#`
prefixes so existing strategies can see structure. Tables flatten to
cell paragraphs. `Document.path` is `gdocs:{id}` and `reader` is
`"gdocs"`.

Wiring `reader: gdocs` into lynguine's `document_segment` compute
function needs a core reader registry (follow-on). Until then call
`read_gdoc` / `gdoc_segment` from application code or a custom compute
hook, using the same `credential_value` binding as the catalogue type.

## Status

Catalogue (CIP-0001) and body reader (CIP-0002) are both in this
package. `document_segment` plugin registration remains a lynguine
follow-on.
