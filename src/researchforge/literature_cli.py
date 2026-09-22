"""Opt-in literature discovery and deterministic evidence verification commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from researchforge.evidence import answer_claims, verify_graph
from researchforge.fixtures import load_fixture_graph, load_graph
from researchforge.literature import (
    CrossrefLiteratureProvider,
    FixtureLiteratureProvider,
    LiteratureProviderError,
)
from researchforge.protocols import LiteratureProvider

literature_app = typer.Typer(
    no_args_is_help=True, help="Discover papers and verify located evidence."
)


@literature_app.command("search")
def search(
    query: Annotated[str, typer.Argument(help="Bibliographic search phrase")],
    provider: Annotated[str, typer.Option("--provider", help="fixture or crossref")] = "fixture",
    limit: Annotated[int, typer.Option("--limit", help="Maximum records (1-100)")] = 10,
) -> None:
    """Search fixed examples or opt in to live Crossref metadata."""
    if provider == "fixture":
        selected: LiteratureProvider = FixtureLiteratureProvider(load_fixture_graph().papers)
    elif provider == "crossref":
        selected = CrossrefLiteratureProvider()
    else:
        raise typer.BadParameter("provider must be fixture or crossref")
    try:
        papers = selected.search(query, limit=limit)
    except (ValueError, LiteratureProviderError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None
    typer.echo(json.dumps([paper.model_dump(mode="json") for paper in papers]))


@literature_app.command("demo")
def demo(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write fixture graph JSON")
    ] = None,
) -> None:
    """Evaluate the bundled synthetic graph and optionally save a copy."""
    graph = load_fixture_graph()
    if output is not None:
        try:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(graph.model_dump_json(indent=2))
        except OSError as error:
            typer.echo(f"could not write output: {error}", err=True)
            raise typer.Exit(1) from None
    decision = answer_claims(graph, tuple(claim.claim_id for claim in graph.claims))
    typer.echo(decision.model_dump_json())


@literature_app.command("verify")
def verify(path: Annotated[Path, typer.Argument(help="Evidence graph JSON")]) -> None:
    """Verify a graph's locators, source hashes, and literal claim support."""
    try:
        graph = load_graph(path)
    except (ValueError, ValidationError, OSError) as error:
        typer.echo(f"invalid evidence graph: {error}", err=True)
        raise typer.Exit(1) from None
    report = verify_graph(graph)
    typer.echo(report.model_dump_json())
    if not report.valid:
        raise typer.Exit(1)
