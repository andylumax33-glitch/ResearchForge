# Contributing to ResearchForge

Thank you for helping make reproducible research easier to audit and recover.

## Before you begin

- Discuss large features or public contract changes in an issue first.
- Keep contributions aligned with the current roadmap phase.
- Never commit credentials, private research data, model outputs, local runtime state, or large datasets.
- Preserve immutable domain values and explicit stage boundaries.

## Development setup

ResearchForge requires Python 3.12+ and `uv`.

```bash
git clone https://github.com/<owner>/ResearchForge.git
cd ResearchForge
uv sync --all-extras --dev
```

## Test-driven workflow

For a behavior change:

1. Add a focused test that fails for the intended reason.
2. Implement the smallest safe change that passes it.
3. Refactor without changing behavior.
4. Add integration or workflow coverage when a persistence or state boundary changes.
5. Review the final diff for secrets, unsafe paths, and accidental generated files.

All changes must pass:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run bandit -q -r src
uv run pytest --cov=researchforge --cov-report=term-missing --cov-fail-under=80
```

Core code coverage must remain at or above 80%. New state transitions and failure modes require tests; coverage percentage alone is not sufficient.

## Design rules

- Create new domain objects instead of mutating existing instances.
- Validate external data at its boundary.
- Keep functions focused and errors explicit.
- Never advance state based solely on a specialist's natural-language claim.
- Store enough provenance to reproduce and audit every accepted transition.
- Treat artifacts and paths as untrusted input.
- Keep external services behind the published provider protocols.
- Do not silently retry non-idempotent work.

## Commits and pull requests

Use Conventional Commits, for example:

```text
feat: add checkpoint recovery
fix: reject stale project versions
test: cover malformed artifact export
docs: clarify approval boundary
```

Pull requests should include:

- the problem and intended behavior;
- design or public-interface changes;
- tests added and commands run;
- security or migration considerations;
- documentation updates, when applicable.

Keep pull requests focused. Do not combine unrelated cleanup with behavior changes.

## Documentation

Update the README or architecture documentation when changing CLI behavior, state semantics, public types, storage contracts, or security boundaries. Do not document future functionality as already available.

By contributing, you agree that your contribution is licensed under Apache-2.0.

