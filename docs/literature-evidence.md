# Literature and evidence in v0.2

ResearchForge separates discovering a paper from verifying a statement about it. A `PaperRecord` is metadata. It cannot support a claim until a source passage, exact quotation, locator, and matching SHA-256 are supplied in an `EvidenceGraph`.

## Repeatable walkthrough

```bash
uv run researchforge literature search railway
uv run researchforge literature demo --output evidence.json
uv run researchforge literature verify evidence.json
```

The bundled graph at [`src/researchforge/data/literature_fixture.json`](../src/researchforge/data/literature_fixture.json) is synthetic and labelled as such. `demo` prints an `AnswerDecision` with `accepted`, `answer`, `citations`, and `reasons`. Editing the quotation or passage without updating its hash makes `verify` exit nonzero. The tests also check missing locators, dangling links, duplicate IDs, unknown claims, and out-of-scope evidence.

For live metadata discovery, use `literature search QUERY --provider crossref --limit 5`. This contacts the fixed Crossref HTTPS API host with a timeout and does not ingest abstracts as evidence. Network errors are reported to the caller. Crossref's [REST API documentation](https://api.crossref.org/) describes `query.bibliographic`, `rows`, and `select` parameters.

## Graph contract

Each graph contains paper records, located source passages, evidence cards, claims, and a scope report. The card's `(paper_id, locator)` must resolve to exactly one passage; its quote must be present in that passage, and its `passage_sha256` must match the UTF-8 passage text. Every claim must link to a card, and the full claim statement must be present in each linked quote. A requested claim may be answered only when its paper is in the scope report.

This deliberately restricts v0.2 to literal claims. A paraphrase, causal inference, or statistical conclusion requires a later human or independent verification gate. A matching hash establishes internal consistency with the supplied text; it does not prove that a publisher published that text. Callers remain responsible for obtaining and licensing source passages.

## Paper2Agent adapter

The [upstream Paper2Agent project](https://github.com/jmiao24/Paper2Agent) currently describes an agent skill that creates MCP tools from papers and their code. ResearchForge does not copy or launch that workflow. An independently generated tool can be registered as a metadata descriptor through `Paper2AgentAdapter.from_manifest(path)`. The manifest is a JSON object with `paper_uri`, `provenance_uri`, `mcp_server_uri`, and a nonempty `tool_names` array. All URIs must be public HTTPS URLs. The adapter reads at most 64 KiB and does not contact the endpoint or execute its tools.

This boundary lets a future sandboxed tool client consume Paper2Agent output without making generated-code execution part of v0.2.
