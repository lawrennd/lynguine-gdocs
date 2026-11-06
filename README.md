# lynguine-gdocs

Google Docs as a lynguine tabular source (`type: gdocs`). One row per
Doc. The type is read-only. Full Doc **body** text is out of scope here
(CIP-0013 later); this catalogue is metadata only.

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

Enable the **Google Drive API** on a Google Cloud project. Create an
**Desktop / Installed** OAuth client (not the offlineimap Web redirect
client unless you know you need it). Add the Google account as a test
user while the consent screen is in Testing.

```bash
pip install 'lynguine-gdocs[oauth]'

python -m lynguine_gdocs.login --name my_google \
  --client-id '....apps.googleusercontent.com' \
  --client-secret '...'
```

Encrypted-file storage needs a master key (lynguine CIP-001A / OS
keyring) and writes under `~/.lynguine/credentials/`.

A Testing OAuth app expires refresh tokens after 7 days. Re-run login
when Drive returns authorization failures after that window.

## YAML

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

## Status

`type: gdocs` catalogue (Drive list) is the first slice. Doc body
extraction is a follow-on requirement.
