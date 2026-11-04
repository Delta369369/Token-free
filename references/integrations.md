# Integrações externas — fronteiras e condições

## Claude Code

Place package folder or `integrations/claude-code/SKILL.md` under `~/.claude/skills/adon-context-efficiency/`. Because the skill invokes the Python package, make its root importable by running commands from the package folder or setting an explicit PYTHONPATH. The skill does not trigger itself: invoke deliberately for session closure/restore. An optional hook can be configured only after validating the user's Claude Code version, event payload and sandbox. Do **not** presume automatic hooks are installed.

## Codex

Place `SKILL.md` within `~/.agents/skills/adon-context-efficiency/` or the project-specific skills directory. Run package commands from the root. Do not alter Codex's native context compaction or automatic cleanup. The skill's checkpoint is durable **cross-session** state; a Codex native compaction is a separate runtime operation.

## GitHub repository context

See `github-workflow.md` for the optional, token-conscious workflow. The ADON package does not create a GitHub token, MCP server, remote index, or GitHub write operation. Prefer the agent's already-connected GitHub app/connector for scoped search and selected file reads; use a local clone when that connector is unavailable. Keep ADON's SQLite database local and record external URLs/commit references only.

## Graphiti

The `--queue-graphiti` event flag adds an explicit *pending* outbox record. `graphiti-pending --project ...` lists records for possible ingestion. There is no network sender in this package. Production adapter must:

1. Check per-project data classification and authorization; perform content minimization/redaction if required.
2. Map event to Graphiti episode with the project namespace/group, event ID as an idempotency reference, event timestamp, kind and original source IDs.
3. Use a locally authorized LLM or a specifically authorized external LLM; Graphiti ingestion may involve model calls and costs.
4. Commit success only after Graphiti confirms ingestion; retry idempotently on error and preserve original event in SQLite.
5. Retrieve results constrained by project and validate links against canonical source records before using them as evidence.

This package is intentionally *not* an untested REST/MCP connector. Graphiti API versions differ and the project's reference server may have inadequate authentication for production. Implement against an audited, pinned Graphiti version. Example queue is safe with no Graphiti installation.

## MinerU / Esdras

Use MinerU as optional parser underneath Esdras. Keep original bytes, immutable source ID, SHA-256, extracted page/block IDs, parser version and any OCR uncertainty. The current MVP provides only source registration/hashing. It does **not** parse PDFs.

## RAGFlow / PageIndex

Use a single `RetrievalProvider` contract. Start with Adon RAG as the default and test RAGFlow and PageIndex as implementations behind that contract. Avoid creating duplicate embeddings/indexes until the A/B test justifies them. This package does **not** embed, rerank or search PDFs.

## CAG and provider cache

Cache manager must distinguish cache-write/read tokens, provider/version, exact stable prompt prefix, per-provider TTL, invalidation when source/constraint changes, and monetary costs. Cache is not assumed to be transferable between OpenAI and Anthropic or between ChatGPT Web and API.

## Token Dashboard

The `usage-add` CLI accepts normalized measured usage records, but it does not automatically parse Codex JSONL, Claude JSONL or live API responses. Native Claude Code token-dashboard can be separately run and its metrics normalized with a dedicated, tested adapter. The v1 telemetry CLI is an ingest/storage/benchmark contract, not a full visual dashboard.

## Codex ChatGPT Web

Optional, experimental, unofficial transport; not installed or called by this package. Needs separate policy and security review. Never rely on browser automation as a substitute for authorized official API access or to evade limits.
