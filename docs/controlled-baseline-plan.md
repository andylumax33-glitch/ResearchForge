# Controlled baseline reproduction: implementation plan

Baseline: main `d2e08d8`; existing suite: 53 passed, 89.07% coverage.
This local plan is the issue-ready scope; no remote issue or merge is implied.

## Reviewable slices

1. Fixed arithmetic baseline: typed input/protocol/request/result/receipt,
   Docker adapter, durable provenance, scoped runtime gate and focused tests.
2. CLI example, real Docker integration job, recovery and failure regression
   coverage, existing quality gates and contributor handoff.

No new states, general revision, validation override, role authority changes,
Paper2Agent coupling or v1 roadmap changes. Existing v0.2 payloads remain readable.

## Compatibility and trust boundary

Controlled execution is opt-in by persisting a `baseline_execution_request`.
After enrollment, ordinary advance and submit must validate the latest request
and its linked result/receipt; a legacy mock cannot satisfy this gate.
Legacy projects keep their existing simulation behavior, which is not evidence
of actual reproduction. No old `verified` record is upgraded retroactively.

New execution records are operational history, not scientific revisions. Resume
preserves this history for enrolled projects; a pending/interrupted request never
becomes success. Retry creates a new request ID. No in-container checkpointing is
claimed. No automatic retries or automatic image pulls.

The first runner accepts only a bounded numeric fixture and fixed program in an
operator-trusted, locally available, immutable Docker image ID. It does not run
arbitrary generated code. Docker provides isolation; ResearchForge supplies
network/read-only/non-root/resource restrictions and checks the evidence.

## Acceptance

- Correct metric within tolerance permits the existing baseline transition.
- Nonzero exit, timeout, missing/malformed/nonfinite metric, bad linkage/hash,
  pending request, or out-of-tolerance result prevents transition.
- Requests are persisted before execution; failures and logs remain artifacts.
- New attempts cannot reuse an earlier successful receipt.
- Recovery does not erase execution history or consumed-attempt accounting.
- Existing v0.2 tests and all repository quality gates pass.
- Real Docker test is distinct from fake-adapter tests; absence is reported,
  never represented as a successful isolated run.
