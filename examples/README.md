# Examples

Phase 1 examples exercise the runtime using deterministic simulated artifacts. They demonstrate orchestration and recovery; they do not perform literature search, call an LLM, train a model, or execute generated code.

## Minimal local workflow

From the repository root:

```bash
uv sync --all-extras --dev
mkdir -p /tmp/researchforge-demo
cd /tmp/researchforge-demo
uv run --project /path/to/ResearchForge researchforge init "Railway pilot"
uv run --project /path/to/ResearchForge researchforge status PROJECT_ID
```

Inspect each command before continuing:

```bash
uv run --project /path/to/ResearchForge researchforge advance --help
uv run --project /path/to/ResearchForge researchforge approve --help
uv run --project /path/to/ResearchForge researchforge resume --help
uv run --project /path/to/ResearchForge researchforge export --help
```

Use `researchforge advance PROJECT_ID --mock` to create the deterministic Phase 1 artifact and
advance stage by stage. Explicitly approve at the human gate. At any point, inspect state with
`status`; restore a recorded checkpoint with `resume PROJECT_ID CHECKPOINT_ID`.

Local runtime state is written beneath the demo workspace and should not be committed. The repository `.gitignore` excludes standard ResearchForge runtime paths.

## Expected safety behavior

Try these scenarios in a disposable workspace:

- submit an artifact missing a required field;
- attempt to skip a state;
- submit a path outside the workspace;
- approve before reaching the human approval gate;
- repeat a decision;
- interrupt a workflow and resume it.

Invalid operations must return a clear error and leave the prior persisted project state unchanged.

## Railway example status

The full railway irregularity example belongs to v1.0.0. Phase 1 uses railway-themed names only to illustrate the generic runtime; no domain model or scientific result is bundled yet.
