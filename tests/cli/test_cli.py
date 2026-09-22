from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from researchforge.cli import app

runner = CliRunner()


def invoke(workspace: Path, *args: str) -> Any:
    return runner.invoke(app, [*args, "--workspace", str(workspace)])


def test_init_and_status_are_machine_readable(tmp_path: Path) -> None:
    initialized = invoke(
        tmp_path, "init", "cli-project", "--goal", "Verify the command-line workflow"
    )
    assert initialized.exit_code == 0, initialized.output
    project_id = json.loads(initialized.stdout)["project_id"]

    status = invoke(tmp_path, "status", project_id)
    assert status.exit_code == 0, status.output
    assert json.loads(status.stdout)["state"] == "INTAKE"


def test_unknown_project_returns_nonzero(tmp_path: Path) -> None:
    result = invoke(tmp_path, "status", "00000000-0000-0000-0000-000000000000")

    assert result.exit_code != 0


def test_cli_mock_workflow_approval_and_export(tmp_path: Path) -> None:
    initialized = invoke(tmp_path, "init", "cli-flow", "--goal", "Run the complete mock workflow")
    project_id = json.loads(initialized.stdout)["project_id"]

    advanced = invoke(tmp_path, "advance", project_id)
    assert advanced.exit_code == 0, advanced.output
    artifact = tmp_path / "stage-result.txt"
    artifact.write_text("verified mock output")
    for _ in range(9):
        advanced = invoke(tmp_path, "advance", project_id, "--artifact", str(artifact))
        assert advanced.exit_code == 0, advanced.output
    blocked = invoke(tmp_path, "advance", project_id)
    assert blocked.exit_code != 0

    approved = invoke(
        tmp_path,
        "approve",
        project_id,
        "--actor",
        "owner",
        "--reason",
        "evidence accepted",
    )
    assert approved.exit_code == 0, approved.output
    released = invoke(tmp_path, "advance", project_id)
    assert released.exit_code == 0, released.output

    archive = tmp_path / "research.zip"
    exported = invoke(tmp_path, "export", project_id, "--output", str(archive))
    assert exported.exit_code == 0, exported.output
    assert archive.is_file()
