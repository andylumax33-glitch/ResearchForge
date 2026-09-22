# Architecture

ResearchForge keeps a local, deterministic runtime. v0.2 adds literature discovery and evidence verification beside the existing orchestration, persistence, and artifact boundaries.

## Runtime shape

```text
CLI
 │
 ▼
Application service ─── State machine ─── Domain contracts
 │                            │
 ├── StateRepository          ├── Stage definitions
 ├── ArtifactStore            ├── Verification gates
 └── Checkpoint service       └── Approval policies
       │
       ├── SQLite
       └── Local JSON artifacts
```

The CLI is an adapter, not the business-logic layer. State transitions run through one application service and one state machine, regardless of whether a future caller is a CLI, API, or web application.

## State model

The forward path is fixed in Phase 1:

```text
INTAKE
→ SCOPING
→ LITERATURE_REVIEW
→ BASELINE_REPRODUCTION
→ HYPOTHESIS_GENERATION
→ EXPERIMENT_DESIGN
→ IMPLEMENTATION
→ EXPERIMENT_EXECUTION
→ ANALYSIS
→ CRITIQUE
→ HUMAN_APPROVAL
→ RELEASE
```

Each `StageDefinition` declares required inputs, required output artifacts, verification gates, and whether human approval is required. Illegal jumps and transitions with invalid artifacts are rejected before persistence.

## Atomic transition contract

Every accepted transition records:

- project and input version;
- source and destination states;
- output artifact identifiers and integrity metadata;
- actor and timestamp;
- verification results;
- budget consumed;
- failure details, when applicable;
- parent checkpoint.

The repository uses optimistic concurrency. A stale caller receives a conflict instead of
overwriting a newer version. Project state, transition history, and checkpoint metadata are
committed atomically; a rejected transition leaves the prior project snapshot untouched.
Content-addressed files written before a database conflict may remain as unreferenced blobs and
are safe to garbage-collect in a later maintenance pass.

## Domain contracts

Public domain values are immutable. The key types are `ResearchProject`, `ResearchState`, `StageDefinition`, `Artifact`, `Evidence`, `Claim`, `ApprovalDecision`, `Checkpoint`, `Budget`, and `TransitionResult`.

Extension boundaries are expressed as protocols:

- `StateRepository` and `ArtifactStore` isolate persistence.
- `ModelProvider` and `LiteratureProvider` reserve future external integrations.
- `SandboxRunner` reserves isolated execution.
- `ResearchSpecialist` provides task-scoped research behavior.
- `VerificationGate` decides whether an artifact set satisfies a stage.

The runtime ships local implementations and a deterministic simulated specialist. v0.2 adds a typed literature provider interface, but does not invoke remote models or execute generated code.

## Literature and evidence boundary

The fixture and opt-in Crossref providers return `PaperRecord` metadata. A separate graph carries `SourcePassage`, `EvidenceCard`, `Claim`, and `ScopeReport` values. Verification checks exact quoted text, passage SHA-256, paper and locator links, claim-to-card links, and search scope. It allows only claims whose complete statement appears in a linked quote. Unknown, changed, or out-of-scope material causes refusal.

At the `LITERATURE_REVIEW` stage, the runtime checks this graph before accepting a `literature_review_result` artifact. A failed graph cannot change project state. Search results alone never satisfy the stage gate. The Paper2Agent adapter validates an external manifest; its generated MCP server is never started by ResearchForge.

These checks establish consistency with a supplied passage, not independent authenticity of the underlying publisher document or scientific validity of the quoted claim.

## Local persistence

SQLite is the source of truth for project state, transitions, decisions, and checkpoints. Artifact payloads are stored as JSON beneath the project workspace. Artifact paths are resolved and verified within that workspace; absolute paths and traversal outside it are rejected.

The persistence protocols are intentionally backend-neutral. PostgreSQL and object storage can be added later without changing domain behavior.

## Reliability and safety invariants

- Schema-invalid data never reaches persistence.
- Required approval cannot be inferred or bypassed.
- Repeated approval or rejection is idempotent or explicitly rejected.
- Budget cannot become negative or exceed its configured limit.
- Corrupt artifacts fail verification before a transition.
- Resume uses a valid checkpoint and never fabricates missing work.
- Structured logs redact credential-like fields and do not contain artifact payloads by default.
- No generated code is executed in Phase 1.

## Deferred components

Real LLM providers, generated-code execution, Docker or remote sandboxes, PostgreSQL, web UI, remote GPU execution, multi-user authorization, and domain packs remain deferred. Their planned integration points are described in the [roadmap](roadmap.md).
