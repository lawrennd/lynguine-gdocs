"""In-process Drive stand-in. No sockets."""

from lynguine_gdocs.reader import DRIVE_FILES, DOC_MIME


def sample_files():
    return [
        {
            "id": "doc-1",
            "name": "First paper",
            "webViewLink": "https://docs.google.com/document/d/doc-1/edit",
            "modifiedTime": "2026-11-05T12:00:00.000Z",
            "createdTime": "2026-10-01T09:00:00.000Z",
            "owners": [
                {"displayName": "Neil", "emailAddress": "neil@example.com"},
            ],
            "shared": True,
            "starred": False,
        },
        {
            "id": "doc-2",
            "name": "Second paper",
            "webViewLink": "https://docs.google.com/document/d/doc-2/edit",
            "modifiedTime": "2026-11-06T08:00:00.000Z",
            "createdTime": "2026-10-15T10:00:00.000Z",
            "owners": [
                {"displayName": "Ada", "emailAddress": ""},
                {"displayName": "", "emailAddress": "ada@example.com"},
            ],
            "shared": False,
            "starred": True,
        },
    ]


class FakeDrive:
    def __init__(self, files=None, pages=None, error=None):
        self.files = list(files if files is not None else sample_files())
        self.pages = pages
        self.error = error
        self.calls = []

    def __call__(self, url, params):
        self.calls.append((url, dict(params)))
        if self.error is not None:
            raise self.error
        assert url == DRIVE_FILES
        assert DOC_MIME in params.get("q", "")
        if self.pages is not None:
            token = params.get("pageToken")
            if token is None:
                return {
                    "files": self.pages[0],
                    "nextPageToken": "page-2",
                }
            if token == "page-2":
                return {"files": self.pages[1]}
            raise AssertionError(f"unexpected pageToken {token}")
        return {"files": self.files}
