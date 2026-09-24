# ResearchForge

**ResearchForge** is an evidence-oriented runtime for reproducible research workflows. Its internal architecture is currently code-named **ScholarOS v4**.

The v0.2 release combines the recoverable runtime with literature metadata discovery and literal, located evidence verification. It does not connect to an LLM, run generated code, or provide a web interface.

The development branch adds an opt-in [controlled baseline reproduction slice](docs/controlled-baseline.md):
a fixed numeric fixture runs through Docker, produces linked evidence, and is checked by the
runtime before advancing. This is not completion of v0.3 or a general generated-code runner.

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
git clone https://github.com/andylumax33-glitch/ResearchForge.git
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

Use `advance` to submit the artifact required by the next stage. `--mock` generates deterministic test artifacts. At `LITERATURE_REVIEW`, a real `--artifact` must contain a verified evidence graph; the mock path uses the bundled synthetic graph. The runtime refuses missing, malformed, or unsafe artifacts without partially changing project state.

```bash
uv run researchforge advance PROJECT_ID --mock
uv run researchforge status PROJECT_ID
```

Search the bundled literature example or opt in to live Crossref bibliographic metadata. Search records do not count as verified evidence:

```bash
uv run researchforge literature search railway
uv run researchforge literature search "railway irregularity" --provider crossref --limit 5
uv run researchforge literature demo --output evidence.json
uv run researchforge literature verify evidence.json
```

The demo is explicitly synthetic. Its answer is allowed only because the claim is a literal quotation from a located passage and the passage hash matches. See [Literature and evidence](docs/literature-evidence.md) for the graph contract, evaluation cases, provider interface, and Paper2Agent adapter boundary.

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

## Capabilities

- Immutable domain models and validated artifact contracts
- Deterministic state transitions and explicit acceptance gates
- SQLite state persistence and local JSON artifact storage
- Optimistic concurrency protection
- Checkpoints, failure records, pause/resume, and portable export
- Human approval and rejection decisions
- Model, literature, sandbox, storage, specialist, and verification extension interfaces
- Deterministic mock artifacts for end-to-end runtime tests
- Structured logs with sensitive-value redaction
- Replaceable fixed-fixture and Crossref metadata providers
- Paper records, scoped source passages, evidence cards, and claim-evidence graph
- Citation/quote integrity checks and evidence-bound refusal
- Metadata-only external Paper2Agent manifest adapter

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

ResearchForge is pre-1.0 software. v0.2 verifies literal support within a supplied graph; it does not independently authenticate external source documents or infer whether a scientific claim is true. Later capabilities must preserve the runtime's auditability and failure-safety guarantees.

## License

Licensed under the [Apache License 2.0](LICENSE).
