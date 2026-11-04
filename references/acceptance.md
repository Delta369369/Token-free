# Plano de aceite / Testes A/B

## Local MVP

- `python -m unittest discover -s tests -v` passes.
- New project cannot read another project's events via CLI.
- A checkpoint cannot reference an event or registered file from another project.
- Constraint revocation increments revision and leaves history.
- Source-file SHA-256 is verified from bytes only on explicit request.
- An oversized checkpoint fails instead of silently removing mandatory rules.
- No action automatically clears chat or calls external services.
- Graphiti queue is offline-only; no network transmission.
- Unknown usage cost remains null/unknown, never 0.

## External integration acceptance

1. Baseline and optimized runs use same task specification and same pass/fail tests.
2. Count all model calls, Graphiti ingestion calls, retries, provider cache tokens, reranking and auxiliary operations.
3. Track quality separately: citation exactness, mandatory-constraint preservation, stale references, regression failures.
4. Report raw and cached token quantities and actual USD billed separately; if a field is unknown say unknown.
5. Compare cost per **validated completed task** and latency, not per isolated prompt.
6. Run controlled tests with data separation, no production legal evidence until controls are audited.

Illustrative starting acceptance targets (not measured): 60% lower input tokens for resume; 70% for point PDF queries; >=40% lower financial task cost for selected repeatable workloads, conditional on no critical regressions. Exhaustive investigations require independently verified coverage, not only top-k RAG.

## Versioning and rollout

1. Audit current Adon modules and source of truth.
2. Integrate Handoff and telemetry without modifying original modules.
3. Add retrieval and optional Graphiti after A/B verification.
4. Integrate MinerU under Esdras using source-backed evidence contract.
5. Evaluate cache and model routing against official native baselines.
6. Enable/adapt each component only on measured net benefit, with rollback.
