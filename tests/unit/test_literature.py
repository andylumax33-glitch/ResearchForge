from __future__ import annotations

import json
from urllib.error import URLError

import pytest
from pydantic import ValidationError

from researchforge.literature import (
    CrossrefLiteratureProvider,
    FixtureLiteratureProvider,
    LiteratureProviderError,
    PaperRecord,
)


def test_fixture_search_is_bounded_and_deterministic() -> None:
    records = (
        PaperRecord(
            paper_id="10.1/first", title="Rail forecasting", source_uri="https://doi.org/10.1/first"
        ),
        PaperRecord(
            paper_id="10.1/second",
            title="Rail validation",
            source_uri="https://doi.org/10.1/second",
        ),
    )
    provider = FixtureLiteratureProvider(records)
    assert provider.search("rail", limit=1) == records[:1]
    assert provider.search("missing") == ()
    with pytest.raises(ValueError):
        provider.search("rail", limit=0)
    with pytest.raises(ValueError):
        provider.search(" ")


def test_paper_rejects_unsafe_source_uri() -> None:
    with pytest.raises(ValidationError):
        PaperRecord(paper_id="x", title="Test", source_uri="file:///private/data")
    with pytest.raises(ValidationError):
        PaperRecord(paper_id="x", title="Test", source_uri="https://192.168.1.1/paper")


def test_crossref_normalizes_metadata_without_certifying_evidence() -> None:
    response = {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/example",
                    "title": ["A study"],
                    "author": [{"given": "Ada", "family": "Lovelace"}],
                    "published": {"date-parts": [[2024, 5]]},
                    "abstract": "<p>Unverified metadata</p>",
                }
            ]
        }
    }
    calls: list[tuple[str, float]] = []

    def transport(url: str, timeout: float) -> bytes:
        calls.append((url, timeout))
        return json.dumps(response).encode()

    provider = CrossrefLiteratureProvider(transport=transport)
    papers = provider.search("rail safety", limit=2)
    assert papers[0].paper_id == "10.1234/example"
    assert papers[0].authors == ("Ada Lovelace",)
    assert papers[0].year == 2024
    assert papers[0].abstract is None
    assert "query.bibliographic=rail+safety" in calls[0][0]
    assert "rows=2" in calls[0][0]
    assert calls[0][1] > 0


def test_crossref_rejects_bad_payload_and_network_error() -> None:
    invalid = CrossrefLiteratureProvider(transport=lambda _url, _timeout: b'{"message": {}}')
    with pytest.raises(LiteratureProviderError):
        invalid.search("rail")
    malformed = CrossrefLiteratureProvider(
        transport=lambda _url, _timeout: json.dumps(
            {"message": {"items": [{"DOI": "10.1/x", "title": ["Demo"], "published": "bad"}]}}
        ).encode()
    )
    with pytest.raises(LiteratureProviderError, match="invalid metadata"):
        malformed.search("rail")

    def offline(_url: str, _timeout: float) -> bytes:
        raise URLError("offline")

    unavailable = CrossrefLiteratureProvider(transport=offline)
    with pytest.raises(LiteratureProviderError, match="unavailable"):
        unavailable.search("rail")
