"""Replaceable bibliographic discovery providers; metadata is not evidence."""

from __future__ import annotations

import json
from collections.abc import Callable
from http.client import HTTPSConnection
from ipaddress import ip_address
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit

from pydantic import Field, field_validator

from researchforge.models import FrozenModel


class LiteratureProviderError(RuntimeError):
    """A provider returned unusable data or could not be reached."""


def validate_public_https(value: str) -> str:
    if value != value.strip() or any(
        character.isspace() or ord(character) < 32 for character in value
    ):
        raise ValueError("URI must not contain whitespace or control characters")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    try:
        is_private_ip = not ip_address(host).is_global
    except ValueError:
        is_private_ip = False
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username
        or parsed.password
        or is_private_ip
        or host.lower() in {"localhost", "127.0.0.1", "::1"}
        or host.endswith((".local", ".localhost", ".internal"))
    ):
        raise ValueError("URI must be a public HTTPS URL without credentials")
    return value


class PaperRecord(FrozenModel):
    paper_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=1000)
    source_uri: str
    authors: tuple[str, ...] = ()
    year: int | None = Field(default=None, ge=1500, le=2200)
    abstract: str | None = None
    provider: str = "fixture"

    @field_validator("source_uri")
    @classmethod
    def validate_source_uri(cls, value: str) -> str:
        return validate_public_https(value)


def _validate_search(query: str, limit: int) -> str:
    cleaned = query.strip()
    if not cleaned or len(cleaned) > 500:
        raise ValueError("query must contain 1-500 non-whitespace characters")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    return cleaned


class FixtureLiteratureProvider:
    def __init__(self, records: tuple[PaperRecord, ...]) -> None:
        self.records = records

    def search(self, query: str, limit: int = 10) -> tuple[PaperRecord, ...]:
        needle = _validate_search(query, limit).casefold()
        return tuple(
            record
            for record in self.records
            if needle in record.title.casefold()
            or any(needle in name.casefold() for name in record.authors)
        )[:limit]


def _http_get(url: str, timeout: float) -> bytes:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "api.crossref.org":
        raise LiteratureProviderError("provider endpoint is not permitted")
    connection = HTTPSConnection("api.crossref.org", timeout=timeout)
    try:
        connection.request(
            "GET",
            f"{parsed.path}?{parsed.query}",
            headers={"User-Agent": "ResearchForge/0.2 (literature metadata)"},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise LiteratureProviderError(f"Crossref returned HTTP {response.status}")
        data: bytes = response.read(1_000_001)
    finally:
        connection.close()
    if len(data) > 1_000_000:
        raise LiteratureProviderError("provider response exceeds 1 MB")
    return data


class CrossrefLiteratureProvider:
    """Opt-in Crossref metadata search. Abstracts are deliberately excluded."""

    def __init__(
        self, *, timeout: float = 10.0, transport: Callable[[str, float], bytes] = _http_get
    ) -> None:
        if not 0 < timeout <= 60:
            raise ValueError("timeout must be between 0 and 60 seconds")
        self.timeout = timeout
        self.transport = transport

    def search(self, query: str, limit: int = 10) -> tuple[PaperRecord, ...]:
        cleaned = _validate_search(query, limit)
        params = urlencode(
            {"query.bibliographic": cleaned, "rows": limit, "select": "DOI,title,author,published"}
        )
        url = f"https://api.crossref.org/works?{params}"
        try:
            raw = self.transport(url, self.timeout)
            payload = json.loads(raw)
            items = payload["message"]["items"]
            if not isinstance(items, list):
                raise TypeError("items must be a list")
            return tuple(self._normalize(item) for item in items[:limit])
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise LiteratureProviderError("Crossref is unavailable") from error
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise LiteratureProviderError("Crossref returned invalid metadata") from error

    @staticmethod
    def _normalize(item: object) -> PaperRecord:
        if not isinstance(item, dict):
            raise TypeError("item must be an object")
        doi = item["DOI"]
        title = item["title"][0]
        if not isinstance(doi, str) or not isinstance(title, str):
            raise TypeError("DOI and title must be strings")
        authors = tuple(
            " ".join(
                part
                for part in (author.get("given"), author.get("family"))
                if isinstance(part, str)
            )
            for author in item.get("author", [])
            if isinstance(author, dict)
        )
        published = item.get("published", {})
        if not isinstance(published, dict):
            raise TypeError("published must be an object")
        date_parts = published.get("date-parts", [])
        year = date_parts[0][0] if date_parts else None
        return PaperRecord(
            paper_id=doi,
            title=title,
            source_uri=f"https://doi.org/{quote(doi, safe='/')}",
            authors=authors,
            year=year,
            provider="crossref",
        )
