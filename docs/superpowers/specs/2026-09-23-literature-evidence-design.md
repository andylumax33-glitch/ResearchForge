# Literature and Evidence v0.2 Design

The approved v0.2 milestone adds literature discovery and evidence-bound claims without changing the twelve-stage runtime contract.

## Options considered

1. Offline fixtures only: fully repeatable, but cannot discover publications.
2. Live search only: useful in practice, but tests depend on changing network results.
3. Offline fixtures plus optional live metadata search: repeatable evaluation and a practical provider boundary. This is the selected design.

## Boundaries

- `literature.py` owns immutable paper records and provider implementations. A bundled fixture provider is the default. An opt-in Crossref provider searches bibliographic metadata over HTTPS with a timeout and bounded results. Search results are discovery records, not verified evidence.
- `evidence.py` owns source passages, evidence cards, claim links, scope reports, verification, and refusal. A card must name an existing paper and locator and quote exact text from the matching passage. The passage hash detects changed source text.
- The graph verifies referential integrity and citation provenance before returning an answer. Unsupported, unverified, or out-of-scope claims produce a refusal with reasons. The runtime may use the verified graph as an artifact, but graph construction itself cannot advance a workflow stage.
- `paper2agent.py` accepts an explicit manifest describing an independently generated Paper2Agent MCP endpoint or artifact. It validates provenance and converts it to an immutable external-tool descriptor. It does not install Paper2Agent, launch its generated code, or assume a stable Python API. Executing external tools remains subject to the future sandbox boundary.
- CLI adds `literature search`, `literature demo`, and `literature verify`. Existing commands and storage schemas remain compatible.

## Data flow

Provider search → paper records → separately supplied source passages → evidence cards with exact quotations → claims linked to cards → graph verification → scoped answer or refusal. A deterministic synthetic fixture exercises the complete flow offline. Search metadata is never promoted to evidence automatically.

## Failure behavior

Malformed provider responses, unsafe URLs, missing locators, changed passages, dangling links, duplicate IDs, and out-of-scope claims fail closed. Network failures are reported as provider errors. Verification is pure and never mutates the runtime. CLI verification exits nonzero when the graph is invalid.

## Acceptance

The fixed fixture produces a supported answer with a citation. Altering a quote or passage hash causes refusal. Unknown claims and scope mismatches cause refusal. Provider normalization and error paths, manifest validation, CLI paths, and all existing runtime tests pass. Coverage stays above 80%, with format, type, security, and CI checks green.
