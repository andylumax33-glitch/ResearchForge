# Controlled baseline reproduction (v0.3 slice)

This is a small vertical slice, **not completion of v0.3 or v1**. A fixed Python
program calculates a mean from a bounded numeric fixture. It tests execution,
provenance, recovery and the runtime gate without models, GPUs or generated code.

## Run the example

Requires a working Linux-container Docker daemon and a trusted Python image.
Install the project with `uv sync --all-extras --dev`. The adapter never installs
Docker, pulls images, passes credentials, or falls back to host execution.
Explicit operator preparation (Bash):

```bash
docker pull python:3.12-alpine
IMAGE_ID=$(docker image inspect python:3.12-alpine --format '{{.Id}}')
uv run researchforge init baseline --goal 'Fixed mean reproduction' --workspace .rf-baseline
```

Copy the returned `project_id` into `PROJECT_ID`. The first three advances are
fixture setup, **not actual literature discovery or scientific validation**:

```bash
PROJECT_ID='<returned project_id>'
uv run researchforge advance "$PROJECT_ID" --workspace .rf-baseline
uv run researchforge advance "$PROJECT_ID" --mock --workspace .rf-baseline
uv run researchforge advance "$PROJECT_ID" --mock --workspace .rf-baseline
uv run researchforge reproduce "$PROJECT_ID" \
  --protocol examples/baseline-protocol.json --image-id "$IMAGE_ID" \
  --advance --workspace .rf-baseline
uv run researchforge status "$PROJECT_ID" --workspace .rf-baseline
uv run researchforge export "$PROJECT_ID" --output baseline-bundle.zip --workspace .rf-baseline
```

PowerShell image ID preparation: `$imageId = docker image inspect python:3.12-alpine --format '{{.Id}}'`.
Use that value for `--image-id`; no shell-specific logic is needed by the adapter.

A passed request with `--advance` reaches the **existing** hypothesis stage.
Without `--advance`, the receipt is saved and the project stays at baseline until
ordinary `advance` rechecks it. Failure returns a nonzero CLI status and never
advances. An unavailable Docker executable is a recorded failure, not a skip in
the production command. A changed protocol/version needs a new execution; the CLI
always generates a new ID and never automatically retries.
Changing any protocol content requires a higher protocol version; an unchanged
protocol may be retried under a new execution ID. Earlier versions stay recorded.

## What is persisted

Five ordinary, immutable Artifact envelopes per completed attempt:

1. `baseline_execution_request`: execution ID, versioned protocol, inline dataset
   manifest, seed, reference/tolerance, timeout and immutable image identity.
2. `baseline_stdout`: produced metrics JSON from the fixed program.
3. `baseline_stderr`: diagnostic output (including nonzero exits).
4. `baseline_execution_result`: exit/timeout/failure, elapsed time, hashes of input
   and protocol, image identity and links to request/stdout/stderr.
5. `baseline_reproduction_result`: typed receipt linked to request and result,
   observed/reference metric, absolute deviation/tolerance and assessment reasons.

All payloads have content-addressed hashes through the existing ArtifactStore;
new typed payloads declare schema version 1. No existing Artifact, checkpoint,
Paper2Agent manifest, state enum or SQLite table format is replaced.

The request is persisted before launching Docker. A crash can therefore leave a
pending request, but cannot produce a passing receipt. Completion is atomically
attached to the project with optimistic concurrency. A concurrent modification
can reject completion; its blobs may remain unreferenced, and the request remains
pending. This slice is synchronous and does not reconcile external jobs.

## Gate and trust boundary

The first execution request enrolls the project. Thereafter, baseline advance
requires the **latest** request's receipt. The runtime checks links and hashes and
recomputes the assessment from the stored output; a claimed `accepted: true`, a
previous success or a legacy mock payload is insufficient. Failed results cannot
be converted to passes by human approval.

Checks are scoped: V1 structure/integrity, V2 execution, and agreement with one
predeclared reference metric. They do **not** establish full V3 scientific
validity, V4 adversarial review, independence of the reference, or truth of a
research conclusion. V1–V4 remains the product framework. Legacy `verified`
transition fields are not reinterpreted as a global scientific verdict.

The image ID identifies the image contents, including Python and dependencies.
Operators must retain/reacquire that image for reproduction; exports do not embed
container images. CPU/kernel identity and independent repeatability across
machines are not claimed. The program version is fixed by `arithmetic-mean-v1`;
seed is recorded even though this arithmetic fixture does not require randomness.

The trusted adapter invokes Docker without a shell, host bind mounts, host
credentials or network access. It requests non-root execution, read-only rootfs,
no capabilities, no new privileges, 32 PIDs, 64 MiB memory/no extra swap and one
CPU. Timeout cleanup addresses only the attempt's named container. Failed cleanup
prevents passing. Operators should inspect unresolved containers after daemon
failure. See [Docker run options](https://docs.docker.com/reference/cli/docker/container/run/).

Only an operator-trusted image and this fixed program are supported. Captured logs
are spooled and capped at 64 KiB per stream; excess is a failure. This bounds
retained output and memory, **not temporary disk growth before process exit**.
This is not a hostile-image sandbox or an arbitrary generated-code execution API.
The local artifact repository and adapters are trusted: hashes establish integrity,
not cryptographic attestation against an operator who can rewrite the database.

## Recovery and budget

Legacy v0.2 projects retain their previous snapshot/simulation behavior. For
enrolled projects, execution artifacts and receipts are operational history that
survives snapshot restore. Restoring a checkpoint does not erase enrollment,
refund attempts or turn incomplete work into success. The earlier stage's missing
non-execution artifacts still need to be supplied under existing stage rules.

Each request conservatively reserves its full timeout against the configured
`compute_seconds_limit`, in addition to previously recorded usage. An incomplete
or failed attempt retains that reservation. Actual elapsed duration is recorded
separately; no claim of accurate CPU billing or global budget settlement is made.
Zero retains the legacy meaning of no configured limit. Pending requests can be
superseded by an explicit new attempt, but users must first ensure old execution
has stopped. This is not in-container checkpoint continuation or scientific
revision. Failed experiment history remains visible in the bundle.

## Verification and remaining scope

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run bandit -q -r src
uv run pytest
RF_DOCKER_IMAGE="$IMAGE_ID" uv run pytest tests/integration/test_baseline.py -k real_docker
```

Without `RF_DOCKER_IMAGE`, the real Docker test explicitly skips; fake-adapter tests
are not evidence of isolation. CI includes a dedicated Docker job that supplies
the image ID, so that job cannot silently pass by skipping the real test.

Not implemented: full experiment engine, arbitrary code/data mounts, multi-seed
aggregation, independent scientific review, general revisions, override,
Director/Auditor orchestration, durable external-job reconciliation, multi-user
authorization or full reproducibility-environment distribution. The original v1
Definition of Done and Paper2Agent roadmap are unchanged.
