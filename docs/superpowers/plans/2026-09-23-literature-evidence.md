# Literature and Evidence v0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish v0.2.0 with repeatable, evidence-bound literature workflows.

**Architecture:** Keep literature retrieval, source verification, and external Paper2Agent provenance in separate modules. Preserve the v0.1 runtime contract and use immutable Pydantic models throughout.

**Tech Stack:** Python 3.12+, Pydantic 2, Typer, urllib, pytest, Ruff, MyPy, Bandit, uv.

## Global Constraints

- Crossref search is opt-in and metadata-only; no auto-promotion to evidence.
- Citation checks use exact source passages and SHA-256 integrity.
- Paper2Agent remains external; no generated-code execution.
- Existing state, CLI, and persisted data remain compatible.

---

### Task 1: Literature provider contracts

**Files:** Create `src/researchforge/literature.py`; modify `src/researchforge/protocols.py`; test `tests/unit/test_literature.py`.

**Interfaces:** `PaperRecord`, `FixtureLiteratureProvider.search(query, limit=10)`, `CrossrefLiteratureProvider.search(query, limit=10)`.

- [ ] Write tests for fixture search, Crossref response normalization, invalid inputs, and provider errors.
- [ ] Run tests and confirm the new tests fail before implementation.
- [ ] Implement immutable records and both providers with bounded HTTPS requests.
- [ ] Run tests, format, type-check, and commit `feat: add replaceable literature providers`.

### Task 2: Evidence graph and refusal

**Files:** Create `src/researchforge/evidence.py`; test `tests/unit/test_evidence.py`.

**Interfaces:** `SourcePassage`, `EvidenceCard`, `EvidenceGraph`, `ScopeReport`, `AnswerDecision`, `verify_graph`, `answer_claims`.

- [ ] Write tests for valid citations, tampered quotes/hashes, dangling links, duplicate IDs, scope mismatch, and refusal.
- [ ] Run tests and confirm failure before implementation.
- [ ] Implement pure graph verification and evidence-bound answer composition.
- [ ] Run tests, format, type-check, and commit `feat: add claim evidence verification`.

### Task 3: External adapter and repeatable example

**Files:** Create `src/researchforge/paper2agent.py`, `examples/literature_fixture.json`, `tests/unit/test_paper2agent.py`, `tests/integration/test_literature_example.py`.

**Interfaces:** `Paper2AgentManifest`, `Paper2AgentAdapter.from_manifest`, `load_fixture_graph`.

- [ ] Write failing tests for external manifest validation and the fixed fixture evaluation.
- [ ] Implement manifest validation and the synthetic fixture loader; keep external tool execution disabled.
- [ ] Run tests and commit `feat: add external paper agent manifest adapter`.

### Task 4: CLI, documentation, and release

**Files:** Modify `src/researchforge/cli.py`, `README.md`, `docs/roadmap.md`, `docs/architecture.md`, `pyproject.toml`, `uv.lock`; test `tests/cli/test_literature_cli.py`.

**Interfaces:** `researchforge literature search|demo|verify`.

- [ ] Write failing CLI tests for search, demo, verify, and invalid graph behavior.
- [ ] Add commands, usage docs, and v0.2.0 version; run tests.
- [ ] Run Ruff, MyPy, Bandit, full pytest coverage, and inspect the diff.
- [ ] Commit changes, push the feature branch, merge to main, tag v0.2.0, create the GitHub release, and verify CI.
