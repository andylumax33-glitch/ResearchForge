from __future__ import annotations

import hashlib
from uuid import uuid4

from researchforge.evidence import (
    EvidenceCard,
    EvidenceGraph,
    ScopeReport,
    SourcePassage,
    answer_claims,
    verify_graph,
)
from researchforge.literature import PaperRecord
from researchforge.models import Claim


def graph_fixture() -> tuple[EvidenceGraph, Claim]:
    paper = PaperRecord(paper_id="10.1/demo", title="Demo", source_uri="https://doi.org/10.1/demo")
    passage = SourcePassage(
        paper_id=paper.paper_id, locator="section 2", text="The model used three seeds."
    )
    card = EvidenceCard(
        paper_id=paper.paper_id,
        locator=passage.locator,
        quote=passage.text,
        passage_sha256=hashlib.sha256(passage.text.encode()).hexdigest(),
    )
    claim = Claim(statement="The model used three seeds.", evidence_ids=(card.evidence_id,))
    graph = EvidenceGraph(
        papers=(paper,),
        passages=(passage,),
        cards=(card,),
        claims=(claim,),
        scope=ScopeReport(query="model reproducibility", included_paper_ids=(paper.paper_id,)),
    )
    return graph, claim


def test_valid_graph_answers_with_located_citation() -> None:
    graph, claim = graph_fixture()
    assert verify_graph(graph).valid
    answer = answer_claims(graph, (claim.claim_id,))
    assert answer.accepted
    assert claim.statement in (answer.answer or "")
    assert answer.citations == ("https://doi.org/10.1/demo (section 2)",)


def test_tampered_quote_or_passage_hash_refuses() -> None:
    graph, claim = graph_fixture()
    bad_quote = graph.cards[0].model_copy(update={"quote": "five seeds"})
    altered = graph.model_copy(update={"cards": (bad_quote,)})
    assert not verify_graph(altered).valid

    unrelated = graph.cards[0].model_copy(update={"quote": "three seeds"})
    assert not verify_graph(graph.model_copy(update={"cards": (unrelated,)})).valid
    assert not answer_claims(altered, (claim.claim_id,)).accepted

    bad_hash = graph.cards[0].model_copy(update={"passage_sha256": "0" * 64})
    altered = graph.model_copy(update={"cards": (bad_hash,)})
    assert not verify_graph(altered).valid


def test_dangling_links_and_duplicate_ids_refuse() -> None:
    graph, claim = graph_fixture()
    dangling = claim.model_copy(update={"evidence_ids": (uuid4(),)})
    altered = graph.model_copy(update={"claims": (dangling,)})
    assert not verify_graph(altered).valid
    assert not answer_claims(altered, (claim.claim_id,)).accepted

    duplicated = graph.model_copy(update={"cards": (graph.cards[0], graph.cards[0])})
    assert not verify_graph(duplicated).valid


def test_missing_locator_and_out_of_scope_refuse() -> None:
    graph, claim = graph_fixture()
    no_locator = graph.cards[0].model_copy(update={"locator": "section 9"})
    altered = graph.model_copy(update={"cards": (no_locator,)})
    assert not verify_graph(altered).valid

    excluded = graph.model_copy(update={"scope": ScopeReport(query="other", included_paper_ids=())})
    assert not answer_claims(excluded, (claim.claim_id,)).accepted
    assert not answer_claims(graph, (uuid4(),)).accepted
