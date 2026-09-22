# ResearchForge

**ResearchForge** is an evidence-oriented runtime for reproducible research workflows. Its internal architecture is currently code-named **ScholarOS v4**.

Phase 1 is deliberately small: it provides a deterministic, recoverable runtime skeleton for moving a research project through explicit stages. It does **not** connect to a real LLM, search literature, run generated code in Docker, or provide a web interface yet.

## Why ResearchForge?

Research work should not advance because an agent says it succeeded. A stage advances only when its declared artifacts validate, its transition is legal, and any required human decision has been recorded. Every transition is stored with its inputs, outputs, actor, validation result, budget usage, failure details, and parent checkpoint.

The Phase 1 workflow is:

```text
INTAKE → SCOPING → LITERATURE_REVIEW → BASELINE_REPRODUCTION
       → HYPOTHESIS_GENERATION → EXPERIMENT_DESIGN → IMPLEMENTATION
       → EXPERIMENT_EXECUTION → ANALYSIS → CRITIQUE
       → HUMAN_APPROVAL → RELEASE
```

## Quick start

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/<owner>/ResearchForge.git
cd ResearchForge
uv sync --all-extras --dev
uv run researchforge --help
```

Create a project and inspect it. `init` prints a JSON snapshot containing the project ID; use that
ID in later commands:

```bash
uv run researchforge init "Railway pilot" --goal "Validate the runtime"
uv run researchforge status PROJECT_ID
```

Use `advance` to submit the artifact required by the next stage. Phase 1 also offers `--mock` to generate a deterministic test artifact. The runtime refuses missing, malformed, or unsafe artifacts without partially changing project state.

```bash
uv run researchforge advance PROJECT_ID --mock
uv run researchforge status PROJECT_ID
```

At a human gate, record the decision explicitly:

```bash
uv run researchforge approve PROJECT_ID --actor researcher
# or
uv run researchforge reject PROJECT_ID --actor researcher
```

Recover from a selected checkpoint recorded in project status, then export a portable bundle:

```bash
uv run researchforge resume PROJECT_ID CHECKPOINT_ID
uv run researchforge export PROJECT_ID --output ./exports/project.zip
```

For a guided walkthrough, see [examples/README.md](examples/README.md). Exact flags are also available through `researchforge <command> --help`.

## Phase 1 capabilities

- Immutable domain models and validated artifact contracts
- Deterministic state transitions and explicit acceptance gates
- SQLite state persistence and local JSON artifact storage
- Optimistic concurrency protection
- Checkpoints, failure records, pause/resume, and portable export
- Human approval and rejection decisions
- Model, literature, sandbox, storage, specialist, and verification extension interfaces
- Deterministic mock artifacts for end-to-end runtime tests
- Structured logs with sensitive-value redaction

## Architecture and roadmap

- [Architecture](docs/architecture.md) explains the runtime boundaries and invariants.
- [Roadmap](docs/roadmap.md) defines the staged path to literature evidence, reproducible experiments, scientific validation, and the railway flagship demo.
- [Contributing](CONTRIBUTING.md) describes the test-first workflow and quality gates.
- [Security](SECURITY.md) explains responsible disclosure and Phase 1 safety boundaries.

## Development

```bash
uv sync --all-extras --dev
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run bandit -q -r src
uv run pytest --cov=researchforge --cov-report=term-missing --cov-fail-under=80
```

## Status

ResearchForge is pre-1.0 software. Phase 1 establishes the runtime contract; later capabilities must preserve its auditability and failure-safety guarantees.

## License

Licensed under the [Apache License 2.0](LICENSE).
