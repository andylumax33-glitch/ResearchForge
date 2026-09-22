"""Pure claim-evidence verification with literal, located source support."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from pydantic import Field

from researchforge.literature import PaperRecord
from researchforge.models import Claim, FrozenModel


class SourcePassage(FrozenModel):
    paper_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    text: str = Field(min_length=1)


class EvidenceCard(FrozenModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    paper_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    passage_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ScopeReport(FrozenModel):
    query: str = Field(min_length=1)
    included_paper_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()


class EvidenceGraph(FrozenModel):
    papers: tuple[PaperRecord, ...]
    passages: tuple[SourcePassage, ...]
    cards: tuple[EvidenceCard, ...]
    claims: tuple[Claim, ...]
    scope: ScopeReport


class VerificationReport(FrozenModel):
    valid: bool
    issues: tuple[str, ...]


class AnswerDecision(FrozenModel):
    accepted: bool
    answer: str | None = None
    citations: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def _has_duplicates(values: tuple[object, ...]) -> bool:
    return len(values) != len(set(values))


def verify_graph(graph: EvidenceGraph) -> VerificationReport:
    """Check provenance and literal support; do not infer scientific truth."""
    issues: list[str] = []
    if not graph.papers or not graph.passages or not graph.cards or not graph.claims:
        issues.append("evidence graph must contain papers, passages, cards, and claims")
    paper_ids = tuple(paper.paper_id for paper in graph.papers)
    passage_keys = tuple((item.paper_id, item.locator) for item in graph.passages)
    card_ids = tuple(card.evidence_id for card in graph.cards)
    claim_ids = tuple(claim.claim_id for claim in graph.claims)
    for label, values in (
        ("paper", paper_ids),
        ("passage", passage_keys),
        ("evidence", card_ids),
        ("claim", claim_ids),
    ):
        if _has_duplicates(values):
            issues.append(f"duplicate {label} identifier")
    papers = set(paper_ids)
    if not graph.scope.included_paper_ids:
        issues.append("scope contains no included papers")
    if len(graph.scope.included_paper_ids) != len(set(graph.scope.included_paper_ids)):
        issues.append("duplicate scoped paper identifier")
    for paper_id in graph.scope.included_paper_ids:
        if paper_id not in papers:
            issues.append(f"scope has unknown paper: {paper_id}")
    passages = {(item.paper_id, item.locator): item for item in graph.passages}
    cards = {card.evidence_id: card for card in graph.cards}
    for passage in graph.passages:
        if passage.paper_id not in papers:
            issues.append(f"passage has unknown paper: {passage.paper_id}")
    for card in graph.cards:
        matched_passage = passages.get((card.paper_id, card.locator))
        if matched_passage is None:
            issues.append(f"evidence has missing locator: {card.evidence_id}")
            continue
        digest = hashlib.sha256(matched_passage.text.encode("utf-8")).hexdigest()
        if digest != card.passage_sha256:
            issues.append(f"evidence has changed passage: {card.evidence_id}")
        if card.quote not in matched_passage.text:
            issues.append(f"evidence quote is absent: {card.evidence_id}")
    for claim in graph.claims:
        if not claim.evidence_ids:
            issues.append(f"claim has no evidence: {claim.claim_id}")
        for evidence_id in claim.evidence_ids:
            matched_card = cards.get(evidence_id)
            if matched_card is None:
                issues.append(f"claim has unknown evidence: {claim.claim_id}")
                continue
            if matched_card.paper_id not in graph.scope.included_paper_ids:
                issues.append(f"claim has evidence outside scope: {claim.claim_id}")
            if claim.statement not in matched_card.quote:
                issues.append(f"claim lacks literal support: {claim.claim_id}")
    return VerificationReport(valid=not issues, issues=tuple(issues))


def answer_claims(graph: EvidenceGraph, claim_ids: tuple[UUID, ...]) -> AnswerDecision:
    report = verify_graph(graph)
    if not report.valid:
        return AnswerDecision(accepted=False, reasons=report.issues)
    if not claim_ids:
        return AnswerDecision(accepted=False, reasons=("no claims requested",))
    claims = {claim.claim_id: claim for claim in graph.claims}
    cards = {card.evidence_id: card for card in graph.cards}
    papers = {paper.paper_id: paper for paper in graph.papers}
    included = set(graph.scope.included_paper_ids)
    statements: list[str] = []
    citations: list[str] = []
    for claim_id in claim_ids:
        claim = claims.get(claim_id)
        if claim is None:
            return AnswerDecision(accepted=False, reasons=(f"unknown claim: {claim_id}",))
        for evidence_id in claim.evidence_ids:
            card = cards[evidence_id]
            if card.paper_id not in included:
                return AnswerDecision(
                    accepted=False,
                    reasons=(f"evidence outside scope: {card.paper_id}",),
                )
            citation = f"{papers[card.paper_id].source_uri} ({card.locator})"
            if citation not in citations:
                citations.append(citation)
        statements.append(claim.statement)
    return AnswerDecision(accepted=True, answer=" ".join(statements), citations=tuple(citations))
