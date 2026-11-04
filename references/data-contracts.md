# Contratos de dados (v1)

## Persistência

Canonical source for **session operations**: SQLite. Original documents remain at their original storage locations; SQLite stores source paths, optional cryptographic digests, identifiers and non-evidentiary summaries. This does not replace the original Adon repository or investigative case management database.

Namespaces: every read/query includes `project`. Tool invocations must use the authenticated project's ID, not trust a requested project name from untrusted documents. CLI boundaries protect accidental cross-project mixing; multi-user authorization is **not** implemented by the local CLI.

### Event

`id`, `project`, `session_id`, `kind`, `title`, `body`, `source_refs[]`, `created_at`, `record_sha256`. Kinds: `decision`, `verified`, `observation`, `hypothesis`, `change`, `error`, `note`.

Events are append-only. A new event can supersede an earlier event by reference; no in-place destructive edits. `sha256` checks payload integrity when compared with the documented canonical JSON signature; it is **not** a cryptographic chain/signature or tamperproof audit log.

### Constraints

`project`, `key`, `revision`, `status=active|revoked`, `text`, `source_ref`, `updated_at`. Every replacement creates a history record; revocation must be explicit. Use source IDs that can be independently checked.

### Checkpoint

`project`, `session_id`, `objective`, `done[]`, `decisions[]`, `pending[]`, `next_action`, `git_commit`, `source_refs[]`, `event_ids[]`. `source_refs` may use `src:<UUID>` for registered sources; these are validated within the project. Strings referencing external systems use external identifiers and are only labels until verified with the external source.

### Usage

`project`, `task_id`, `run_id`, `provider`, `model`, `module`, `input_uncached`, `cache_read`, `cache_write`, `output_tokens`, `billed_usd`, `elapsed_ms`, `quality_pass`, `retries`, `source`.

Input categories must be **disjoint**. Do not report cache-read tokens again inside `input_uncached`. Some platforms use overlapping counters; normalize before import and record the source.

`billed_usd=null` means unknown. A subscription's API-equivalent usage is *not* a billed charge. Record actual billed amounts only when known. Benchmark aggregates data explicitly supplied; it does not infer any provider pricing.

## APIs to integrate later

- `HandoffStore`: save_event, save_constraint, save_checkpoint, retrieve_checkpoint, search_events, get_event, list_constraints.
- `EvidenceProvider`: get_original, verify_digest, resolve_page_block; returns source-backed immutable references.
- `RetrievalProvider`: lexical_search, semantic_search, optional_tree_search; returns `EvidencePack`.
- `GraphIndex`: ingest_eligible_event, find_entities, find_relationships, temporal_search; source-linked only.
- `PromptCacheManager`: lookup_context, build_stable_prefix, record_cache_usage, invalidate_by_version.
- `ModelTransport`: call(provider/model, authorized_tools, context_pack, expected_format), returns standardized measured usage.
- `TelemetrySink`: record_usage, build_task_report, compare_paired_tasks.
- `PolicyEngine`: advise_continue_compact_checkpoint, advise_route; no side effects.

## EvidencePack (future contract)

Each excerpt must carry `project`, `source_id`, `source_sha256`, `document_version`, `page_or_location`, `exact_text`, `extraction_method`, `confidence_when_available`, and `retrieved_at`. A semantic hit alone does not authorize asserting a factual conclusion. Models must cite the originals, not their own summaries.

## Confidentiality

The reference local DB is **not encrypted at rest**. Use full-disk encryption, OS ACLs and dedicated workspace separation; for multi-user or production deployment build per-user authorization and a secured storage service. No automatic external data transmission exists in v1.
