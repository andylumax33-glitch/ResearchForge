from __future__ import annotations

import subprocess
from unittest.mock import patch

from researchforge.baseline import BaselineProtocol, DatasetManifest, ExecutionRequest
from researchforge.docker_runner import DockerBaselineRunner


def attempt() -> ExecutionRequest:
    return ExecutionRequest(
        protocol=BaselineProtocol(dataset=DatasetManifest(values=(1, 2, 3))),
        image_id="sha256:" + "a" * 64,
    )


def test_missing_docker_fails_closed() -> None:
    with patch("researchforge.docker_runner.shutil.which", return_value=None):
        result = DockerBaselineRunner().execute(attempt())
    assert result.exit_code is None
    assert result.failure


def test_docker_command_has_isolation_and_cleanup() -> None:
    with (
        patch("researchforge.docker_runner.shutil.which", return_value="/usr/bin/docker"),
        patch(
            "researchforge.docker_runner.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0),
        ) as run,
    ):
        result = DockerBaselineRunner().execute(attempt())
    command = run.call_args_list[0].args[0]
    for flag in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--pull=never",
        "--security-opt=no-new-privileges",
        "--memory=64m",
        "--pids-limit=32",
    ):
        assert flag in command
    assert "--mount" not in command
    assert "--volume" not in command
    assert run.call_args_list[-1].args[0][1:3] == ["rm", "--force"]
    assert result.exit_code == 0


def test_timeout_still_removes_only_named_container() -> None:
    request = attempt()
    with (
        patch("researchforge.docker_runner.shutil.which", return_value="/usr/bin/docker"),
        patch(
            "researchforge.docker_runner.subprocess.run",
            side_effect=[
                subprocess.TimeoutExpired("docker", 10),
                subprocess.CompletedProcess([], 0),
            ],
        ) as run,
    ):
        result = DockerBaselineRunner().execute(request)
    assert result.timed_out
    assert result.exit_code is None
    assert run.call_args_list[-1].args[0][-1] == f"researchforge-{request.execution_id}"


def test_cleanup_failure_does_not_report_success() -> None:
    with (
        patch("researchforge.docker_runner.shutil.which", return_value="/usr/bin/docker"),
        patch(
            "researchforge.docker_runner.subprocess.run",
            side_effect=[
                subprocess.CompletedProcess([], 0),
                OSError("daemon gone"),
            ],
        ),
    ):
        result = DockerBaselineRunner().execute(attempt())
    assert result.failure == "container cleanup could not be confirmed"
