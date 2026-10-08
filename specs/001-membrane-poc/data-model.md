# Data model 001 — PROPOSED

Planning-only companion to `plan.md`; not approved for migration or implementation. Five node processes use five separate SQLite files, each with WAL and `PRAGMA foreign_keys=ON`. Numeric times are UTC Unix milliseconds; IDs are lowercase hex unless noted. Item text, rules, labels, weights, and reasons never enter peer events.

## Tables (one node)

| Table | Key / fields | Ownership and constraint |
|---|---|---|
| `items` | PK `item_id` (16 hex); `canonical_url`, `title`, `lede`, `source`, `published_ms`, `first_seen_ms`, `text_hash` (SHA-256 of canonical local title+lede), `content_key` (64-bit hex string) | Local ingest only. URL-only item ID stays stable across headline edits; a text change invalidates feature cache. Text stays local. |
| `item_groups` | PK `(item_id, group_version)`; `representative_id`, `distance`, `group_version` | Derived local near-duplicate hint. A changing representative must not rewrite signed vote IDs; grouping is recomputable. |
| `features` | PK `(item_id, text_hash, model_version)`; `embedding_cache_key`, `manipulation_score`, `trigger_codes_json` | Scores/trigger codes local. Only the demo **fixture** cache is shared read-only among nodes; live-item features are node-private and keyed by model version and text hash, not item ID alone. |
| `labels` | PK `(owner_id, item_id, labeled_ms)`; `vote` keep/kill, `mode` blind/peers_visible/relabel, `eval_split` | Own labels only; chronological history retained for later blind relabel. A held-out or later relabel is never visible to model fitting at an earlier cutoff. |
| `rules` | PK `rule_id`; `kind` block/allow, `predicate_type`, `predicate_value`, `priority`, `position`, `enabled` | Local sovereign rules; conflict resolution defined in plan §4. |
| `peers` | PK `author_id`; `public_key`, `enabled`, `revoked_ms`, `last_seq`, `last_seen_ms` | Pinned keys, unilateral trust; no discovery or transitivity. A revoked peer's old votes remain auditable but receive weight zero. |
| `events` | PK `(author_id, seq)`; `event_id` UNIQUE, `kind`, `item_id`, `poll_id`, `vote`, `confidence_bp`, `issued_ms`, `signature`, `received_ms`, `status` | Verified append-only inbox, independent per author. First accepted event remains stored; conflicting same-author/same-sequence variant cannot replace it and goes to `event_conflicts`. Both are excluded from aggregation after equivocation. |
| `event_conflicts` | PK `event_id`; `author_id`, `seq`, `reason`, `received_ms`, `signed_bytes` | Bounded local evidence of equivocation; has no aggregation path. Do not claim both conflicting variants fit into the unique-key `events` table. |
| `polls` | PK `poll_id`; `item_id`, `created_ms`, `status` | Local invitation/aggregation. Peer invitations are events; no globally shared verdict row. |
| `verdicts` | PK `(item_id, policy_version, label_cutoff_ms)`; `preference_score`, `manipulation_score`, `class`, `reasons_json` | Local decision cache only; peer-assisted order and contributions recomputed on roster/vote changes. No fused persisted score. |
| `captures` | PK `snapshot_sha256`; `source_manifest_sha256`, `captured_ms`, `corpus_sha256`, `model_version` | Fixture reproducibility metadata; not exchanged. |

Foreign keys apply within one node; `events.item_id` intentionally has **no foreign key** because a legitimate peer can vote on an unknown item. Such an event stays verified but cannot influence a feed item until the node independently ingests that same `item_id`. `polls.item_id` does reference local `items`. Avoid derived global vote-state tables: latest valid event per `(author_id,item_id)` at the evaluation cutoff is selected by `seq`; `poll_id` filters poll responses. Revocation is local state, not an event forwarded to peers.

## Ownership and deletion

Node DB path, private signing key path (permissions 0600), and the read-only fixture cache path must be configured separately per process. Import never opens another node DB. Resetting a node destroys *only* that node's data; fixture text is shared solely because all five demo nodes intentionally mount the same local snapshot. Wire events contain hashes of public URLs and can disclose reading interests by dictionary attack; no private inbox or IMAP during the POC.

## Migration / integrity contract

Schema version in `PRAGMA user_version`, transactionally upgraded; unknown future version refuses startup. Each receive transaction verifies strict JSON schema, signature and pinned author, checks idempotent `(author_id,seq)`, and commits the event/peer watermark atomically. A different event with the same author and sequence stores the conflicting signed bytes in `event_conflicts` and marks the original event excluded; both are absent from aggregate. Other invalid events go to a bounded local quarantine log (with cause and event ID, no body); they cannot mutate votes, trust or gate. Restarting after an acknowledged event cannot lose it. SQLite backup/restore is per node, not replication.
