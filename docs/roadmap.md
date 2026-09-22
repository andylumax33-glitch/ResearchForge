# Roadmap

ResearchForge evolves in independently testable releases. Later phases may extend the runtime but must retain deterministic state transitions, evidence provenance, explicit approvals, and recoverability.

## v0.1.0 — Runtime Skeleton

- Python 3.12 project with CLI and immutable domain contracts
- Deterministic research state machine
- SQLite state repository and local artifact store
- Project creation, inspection, advancement, approval/rejection, resume, and export
- Atomic transitions, optimistic concurrency, checkpoints, failure records, and budget tracking
- Simulated specialist/runner for deterministic workflow tests
- CI quality, type, security, test, and 80% coverage gates

No real LLM, literature retrieval, generated-code execution, Docker, or web UI is included.

## v0.2.0 — Literature + Evidence

- Shipped: replaceable fixed-fixture and opt-in Crossref bibliographic providers
- Shipped: paper records, located passages, evidence cards, and scope reports
- Shipped: Claim–Evidence Graph with literal quote, hash, and citation checks
- Shipped: evidence-bound answers that refuse unsupported or out-of-scope claims
- Shipped: external Paper2Agent manifest adapter without copied implementation
- Shipped: fixed synthetic literature fixture and repeatable evaluation

This version verifies internal provenance and exact quotations. Independent retrieval and authentication of a publisher's full text remains a future extension.

## v0.3.0 — Reproducible Experiments

- Dataset manifests and frozen experiment protocols
- Environment locks, seed policies, and compute budgets
- Isolated sandbox adapter with network, time, memory, and filesystem restrictions
- Baseline reproduction, test-driven experiments, multiple seeds, logs, and metrics
- Interruption recovery and portable reproducibility bundles

## v0.4.0 — Scientific Validation

- Data Analyst, Statistician, Critic, and task-scoped review committee
- Effect sizes, significance tests, ablation checks, and leakage checks
- Claim–Evidence consistency audit
- Review–rebuttal loop capped at three rounds
- Independent release gate

## v1.0.0 — Railway Flagship

- Railway irregularity prediction domain pack
- End-to-end literature, baseline, hypothesis, experiment, analysis, review, and report workflow
- ScholarBench-lite comparisons with direct-model, single-agent, and fixed multi-agent baselines
- Complete documentation, demonstration, and reproducibility bundle

## Explicitly deferred beyond v1

Agent marketplaces, self-evolving agents, a general-purpose knowledge-graph platform, a custom workflow language, automatic publication, unsupervised release, and a bespoke container or messaging platform are not roadmap commitments.
