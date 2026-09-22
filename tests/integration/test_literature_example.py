from __future__ import annotations

from researchforge.evidence import answer_claims, verify_graph
from researchforge.fixtures import load_fixture_graph
from researchforge.literature import FixtureLiteratureProvider


def test_packaged_example_is_searchable_and_cited() -> None:
    graph = load_fixture_graph()
    results = FixtureLiteratureProvider(graph.papers).search("railway")
    assert len(results) == 1
    assert verify_graph(graph).valid
    answer = answer_claims(graph, (graph.claims[0].claim_id,))
    assert answer.accepted
    assert answer.citations[0].endswith("(passages[0])")
