"""In-process Docs API stand-in. No sockets."""

from lynguine_gdocs.body import DOCS_GET


def sample_docs_payload():
    return {
        "title": "Sample paper",
        "revisionId": "rev-1",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "elements": [
                            {"textRun": {"content": "Introduction\n"}},
                        ],
                    }
                },
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "elements": [
                            {
                                "textRun": {
                                    "content": (
                                        "First paragraph with enough words that "
                                        "the CIP-0013 text layer counts as present "
                                        "rather than sparse for a single page Doc. "
                                        "Extra filler keeps the word count above "
                                        "the default thirty words per page threshold "
                                        "used by classify_text_layer.\n"
                                    )
                                }
                            },
                        ],
                    }
                },
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "elements": [
                            {
                                "textRun": {
                                    "content": (
                                        "Second paragraph continues the discussion "
                                        "so pub_dialogue.v1 can form body chunks from "
                                        "substantive paragraph text without falling "
                                        "back to an empty result.\n"
                                    )
                                }
                            },
                        ],
                    }
                },
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "elements": [{"textRun": {"content": "\n"}}],
                    }
                },
                {
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Cell A\n"
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Cell B\n"
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                ]
                            }
                        ]
                    }
                },
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "TITLE"},
                        "elements": [{"textRun": {"content": "Appendix\n"}}],
                    }
                },
            ]
        },
    }


def empty_docs_payload():
    return {
        "title": "Empty",
        "revisionId": "rev-0",
        "body": {"content": []},
    }


class FakeDocs:
    def __init__(self, payload=None, error=None):
        self.payload = payload if payload is not None else sample_docs_payload()
        self.error = error
        self.calls = []

    def __call__(self, url, params):
        self.calls.append((url, dict(params)))
        if self.error is not None:
            raise self.error
        assert url.startswith(DOCS_GET.split("{")[0])
        return self.payload
