# Security Policy

## Supported versions

ResearchForge is pre-1.0. Security fixes are applied to the latest tagged release and the `main` branch.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's **Security → Report a vulnerability** private reporting flow for this repository. Include:

- affected version or commit;
- impact and threat scenario;
- minimal reproduction steps;
- suggested mitigation, if known.

Do not include real credentials, private datasets, or personally identifying information in the report. Maintainers should acknowledge a complete report within seven days and coordinate disclosure after a fix is available.

## Phase 1 security boundary

Phase 1 is a local runtime skeleton. It does not execute generated code, invoke real model providers, search the network, start containers, or expose a web server. The simulated specialist exists only for deterministic tests and examples.

The runtime nevertheless treats local input as untrusted:

- artifact schemas are validated before state changes;
- artifact locations must remain inside the configured workspace;
- absolute paths and traversal attempts are rejected;
- SQLite updates use transactions and optimistic concurrency;
- approval-required transitions cannot be bypassed;
- credential-like values are redacted from structured logs;
- exports include declared project artifacts, not arbitrary filesystem content.

## User responsibilities

- Keep the workspace and SQLite database access restricted to intended users.
- Do not place API keys or confidential datasets in artifact JSON.
- Inspect exported bundles before sharing them.
- Verify third-party dependencies and upgrades in your deployment environment.
- Do not represent Phase 1 as a secure sandbox for untrusted code.

Future sandbox and network integrations must ship with explicit resource, filesystem, credential, and egress controls before they are enabled by default.

