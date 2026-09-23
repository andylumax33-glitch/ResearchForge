from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from researchforge.baseline import RunnerOutput
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
    for stage_number in range(9):
        arguments = ("--mock",) if stage_number == 1 else ("--artifact", str(artifact))
        advanced = invoke(tmp_path, "advance", project_id, *arguments)
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


def test_reproduce_cli_runs_gate_and_outputs_receipt(tmp_path: Path) -> None:
    initialized = invoke(tmp_path, "init", "controlled")
    project_id = json.loads(initialized.stdout)["project_id"]
    for _ in range(3):
        assert invoke(tmp_path, "advance", project_id, "--mock").exit_code == 0
    protocol = Path(__file__).parents[2] / "examples" / "baseline-protocol.json"
    with patch(
        "researchforge.cli.DockerBaselineRunner.execute",
        return_value=RunnerOutput(exit_code=0, stdout='{"mean":2}'),
    ):
        result = invoke(
            tmp_path,
            "reproduce",
            project_id,
            "--protocol",
            str(protocol),
            "--image-id",
            "sha256:" + "a" * 64,
            "--advance",
        )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["assessment"]["accepted"]
    assert json.loads(invoke(tmp_path, "status", project_id).stdout)["state"] == (
        "HYPOTHESIS_GENERATION"
    )


def test_reproduce_cli_backend_failure_is_recorded(tmp_path: Path) -> None:
    initialized = invoke(tmp_path, "init", "controlled-failure")
    project_id = json.loads(initialized.stdout)["project_id"]
    for _ in range(3):
        assert invoke(tmp_path, "advance", project_id, "--mock").exit_code == 0
    protocol = Path(__file__).parents[2] / "examples" / "baseline-protocol.json"
    with patch("researchforge.docker_runner.shutil.which", return_value=None):
        result = invoke(
            tmp_path,
            "reproduce",
            project_id,
            "--protocol",
            str(protocol),
            "--image-id",
            "sha256:" + "a" * 64,
            "--advance",
        )
    assert result.exit_code == 1
    assert not json.loads(result.stdout)["assessment"]["accepted"]
    status = json.loads(invoke(tmp_path, "status", project_id).stdout)
    assert status["state"] == "BASELINE_REPRODUCTION"
    assert "Docker executable unavailable" in status["failure_reason"]
    assert invoke(tmp_path, "advance", project_id, "--mock").exit_code == 1


def test_reproduce_cli_rejects_missing_protocol(tmp_path: Path) -> None:
    project_id = json.loads(invoke(tmp_path, "init", "bad-protocol").stdout)["project_id"]
    result = invoke(
        tmp_path,
        "reproduce",
        project_id,
        "--protocol",
        str(tmp_path / "missing"),
        "--image-id",
        "sha256:" + "a" * 64,
    )
    assert result.exit_code == 1
    assert "64 KiB" in result.output
