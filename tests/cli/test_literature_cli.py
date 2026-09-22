from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from researchforge.cli import app
from researchforge.fixtures import load_fixture_graph
from researchforge.literature import PaperRecord

runner = CliRunner()


def test_fixture_search_and_demo() -> None:
    searched = runner.invoke(app, ["literature", "search", "railway"])
    assert searched.exit_code == 0, searched.output
    assert len(json.loads(searched.stdout)) == 1

    demo = runner.invoke(app, ["literature", "demo"])
    assert demo.exit_code == 0, demo.output
    assert json.loads(demo.stdout)["accepted"] is True


def test_verify_rejects_corrupted_graph(tmp_path: Path) -> None:
    graph = load_fixture_graph()
    path = tmp_path / "graph.json"
    path.write_text(graph.model_dump_json())
    valid = runner.invoke(app, ["literature", "verify", str(path)])
    assert valid.exit_code == 0, valid.output
    assert json.loads(valid.stdout)["valid"] is True

    changed = graph.cards[0].model_copy(update={"quote": "invented result"})
    path.write_text(graph.model_copy(update={"cards": (changed,)}).model_dump_json())
    invalid = runner.invoke(app, ["literature", "verify", str(path)])
    assert invalid.exit_code != 0
    assert json.loads(invalid.stdout)["valid"] is False

    other = PaperRecord(
        paper_id="researchforge:synthetic:other",
        title="Other synthetic paper",
        source_uri="https://example.org/other",
    )
    out_of_scope = graph.scope.model_copy(update={"included_paper_ids": (other.paper_id,)})
    path.write_text(
        graph.model_copy(
            update={"papers": (*graph.papers, other), "scope": out_of_scope}
        ).model_dump_json()
    )
    scoped = runner.invoke(app, ["literature", "verify", str(path)])
    assert scoped.exit_code != 0
    assert json.loads(scoped.stdout)["valid"] is False
