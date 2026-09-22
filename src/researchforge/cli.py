"""ResearchForge command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from researchforge.artifacts import FileArtifactStore
from researchforge.fixtures import load_fixture_graph
from researchforge.literature_cli import literature_app
from researchforge.models import ResearchProject, ResearchState
from researchforge.repositories import ProjectNotFoundError, SQLiteStateRepository
from researchforge.service import ResearchRuntime, StageValidationError
from researchforge.state_machine import DEFAULT_STAGES

app = typer.Typer(no_args_is_help=True, help="Evidence-grounded research workflow runtime.")
app.add_typer(literature_app, name="literature")
WorkspaceOption = Annotated[Path, typer.Option("--workspace", help="Runtime data directory")]


def _runtime(workspace: Path) -> ResearchRuntime:
    return ResearchRuntime(
        SQLiteStateRepository(workspace / "state.db"),
        FileArtifactStore(workspace / "artifacts"),
    )


def _parse_project_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        typer.echo(f"Project not found: {value}", err=True)
        raise typer.Exit(1) from None


def _project(runtime: ResearchRuntime, value: str) -> ResearchProject:
    try:
        return runtime.get_project(_parse_project_id(value))
    except ProjectNotFoundError:
        typer.echo(f"Project not found: {value}", err=True)
        raise typer.Exit(1) from None


def _json_project(project: ResearchProject) -> str:
    payload = project.model_dump(mode="json")
    payload["state"] = project.state.name
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


@app.command("init")
def initialize(
    name: Annotated[str, typer.Argument(help="Project name")],
    goal: Annotated[str, typer.Option("--goal", "-g", help="Research goal")] = "Define goal",
    json_output: Annotated[bool, typer.Option("--json")] = False,
    workspace: WorkspaceOption = Path(".researchforge"),
) -> None:
    """Create a research project in the intake state."""
    project = _runtime(workspace).create_project(name=name, goal=goal)
    _ = json_output
    typer.echo(_json_project(project))


@app.command()
def status(
    project_id: Annotated[str, typer.Argument()],
    json_output: Annotated[bool, typer.Option("--json")] = False,
    workspace: WorkspaceOption = Path(".researchforge"),
) -> None:
    """Show the current immutable project snapshot."""
    _ = json_output
    typer.echo(_json_project(_project(_runtime(workspace), project_id)))


@app.command()
def advance(
    project_id: Annotated[str, typer.Argument()],
    actor: Annotated[str, typer.Option("--actor", "-a")] = "mock-specialist",
    artifact: Annotated[Path | None, typer.Option("--artifact")] = None,
    mock: Annotated[bool, typer.Option("--mock")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    workspace: WorkspaceOption = Path(".researchforge"),
) -> None:
    """Verify and advance exactly one workflow stage."""
    runtime = _runtime(workspace)
    project = _project(runtime, project_id)
    if DEFAULT_STAGES[project.state].required_artifact_kinds:
        if artifact is None and not mock:
            raise typer.BadParameter("--artifact or --mock is required")
        if artifact is not None:
            content = artifact.read_bytes()
            filename = artifact.name
        elif project.state is ResearchState.LITERATURE_REVIEW:
            content = load_fixture_graph().model_dump_json().encode()
            filename = "mock-evidence.json"
        else:
            content = f"mock result for {project.project_id} at {project.state.value}".encode()
            filename = "mock-result.txt"
    try:
        if DEFAULT_STAGES[project.state].required_artifact_kinds:
            result = runtime.submit_and_advance(
                project.project_id,
                actor=actor,
                filename=filename,
                content=content,
            )
        else:
            result = runtime.advance(project.project_id, actor=actor)
    except StageValidationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None
    _ = json_output
    typer.echo(_json_project(result.project))


@app.command()
def approve(
    project_id: Annotated[str, typer.Argument()],
    actor: Annotated[str, typer.Option("--actor", "-a")],
    reason: Annotated[str, typer.Option("--reason", "-r")] = "approved",
    json_output: Annotated[bool, typer.Option("--json")] = False,
    workspace: WorkspaceOption = Path(".researchforge"),
) -> None:
    runtime = _runtime(workspace)
    project = runtime.approve(_project(runtime, project_id).project_id, actor=actor, reason=reason)
    _ = json_output
    typer.echo(_json_project(project))


@app.command()
def reject(
    project_id: Annotated[str, typer.Argument()],
    actor: Annotated[str, typer.Option("--actor", "-a")],
    reason: Annotated[str, typer.Option("--reason", "-r")] = "rejected",
    json_output: Annotated[bool, typer.Option("--json")] = False,
    workspace: WorkspaceOption = Path(".researchforge"),
) -> None:
    runtime = _runtime(workspace)
    project = runtime.reject(_project(runtime, project_id).project_id, actor=actor, reason=reason)
    _ = json_output
    typer.echo(_json_project(project))


@app.command()
def resume(
    project_id: Annotated[str, typer.Argument()],
    checkpoint_id: Annotated[UUID, typer.Argument()],
    json_output: Annotated[bool, typer.Option("--json")] = False,
    workspace: WorkspaceOption = Path(".researchforge"),
) -> None:
    runtime = _runtime(workspace)
    project = runtime.resume(_project(runtime, project_id).project_id, checkpoint_id)
    _ = json_output
    typer.echo(_json_project(project))


@app.command("export")
def export_project(
    project_id: Annotated[str, typer.Argument()],
    destination: Annotated[Path, typer.Option("--output", "-o")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
    workspace: WorkspaceOption = Path(".researchforge"),
) -> None:
    runtime = _runtime(workspace)
    path = runtime.export(_project(runtime, project_id).project_id, destination)
    _ = json_output
    typer.echo(json.dumps({"path": str(path)}))


if __name__ == "__main__":
    app()
