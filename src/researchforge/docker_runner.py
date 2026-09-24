"""Fixed-program Docker adapter. No host execution fallback or automatic pull."""

from __future__ import annotations

import json
import shutil

# Fixed executable and argv, never a shell.
import subprocess  # nosec B404
import tempfile
import time

from researchforge.baseline import ExecutionRequest, RunnerOutput

# The trusted image must supply Python. No user-supplied program or command is accepted.
PROGRAM = (
    "import json,random,statistics,sys; "
    "p=json.load(sys.stdin); random.seed(p['seed']); "
    "print(json.dumps({'mean':statistics.mean(p['values'])},allow_nan=False))"
)
MAX_LOG_BYTES = 65536


class DockerBaselineRunner:
    def execute(self, request: ExecutionRequest) -> RunnerOutput:
        docker = shutil.which("docker")
        if docker is None:
            return RunnerOutput(exit_code=None, failure="Docker executable unavailable")
        name = f"researchforge-{request.execution_id}"
        command = [
            docker,
            "run",
            "--pull=never",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user=65534:65534",
            "--pids-limit=32",
            "--memory=64m",
            "--memory-swap=64m",
            "--cpus=1",
            "--log-driver=none",
            "-i",
            "--entrypoint=python",
            request.image_id,
            "-I",
            "-B",
            "-c",
            PROGRAM,
        ]
        started = time.monotonic()
        exit_code: int | None = None
        timed_out = False
        failure: str | None = None
        # Spool output rather than buffering arbitrary container output in memory.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            try:
                completed = subprocess.run(  # nosec B603
                    command,
                    input=json.dumps(
                        {"values": request.protocol.dataset.values, "seed": request.protocol.seed}
                    ).encode(),
                    stdout=stdout,
                    stderr=stderr,
                    timeout=request.protocol.timeout_seconds,
                    check=False,
                )
                exit_code = completed.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
            except OSError as error:
                failure = f"Docker invocation failed: {type(error).__name__}"
            finally:
                try:
                    # Cleanup targets only this request's named container.
                    cleanup = subprocess.run(  # nosec B603
                        [docker, "rm", "--force", name],
                        capture_output=True,
                        timeout=10,
                        check=False,
                    )
                    if cleanup.returncode and exit_code == 0:
                        failure = "container cleanup could not be confirmed"
                except (OSError, subprocess.TimeoutExpired):
                    failure = "container cleanup could not be confirmed"
            stdout.seek(0)
            stderr.seek(0)
            output = stdout.read(MAX_LOG_BYTES + 1)
            errors = stderr.read(MAX_LOG_BYTES + 1)
            if max(len(output), len(errors)) > MAX_LOG_BYTES:
                failure = "container output exceeds capture limit"
            return RunnerOutput(
                exit_code=exit_code,
                stdout=output[:MAX_LOG_BYTES].decode(errors="replace"),
                stderr=errors[:MAX_LOG_BYTES].decode(errors="replace"),
                timed_out=timed_out,
                failure=failure,
                elapsed_seconds=time.monotonic() - started,
            )
