# Ingest, classifier and UI API contract — PROPOSED

This document fixes interfaces for review, not code. All HTTP routes are bound to loopback; authentication from another local OS user is *not* guaranteed by loopback alone, so the POC must run under one trusted user account and state this limit. A later multi-user deployment would need authorization and process isolation.

## Python ingest and scores

`ingest(source, snapshot=None) -> Iterable[Item]`: fixture and RSS adapters yield `{item_id, canonical_url, title, lede, source, published_ms, text_hash}`; local text stays in the node. Snapshot import is idempotent by item ID; edits to title/lede update text hash and invalidate that item's cached features, not its URL-derived ID. Daily capture merges by item ID before a deterministic source quota; pin snapshot bytes and input feed manifest checksum. Live RSS never enters the eval snapshot.

`extract(item, model_version) -> FeatureSet`: read the shared read-only **fixture** cache or populate a **node-private live-item** cache keyed by `(item_id,text_hash,model_version)` with a model2vec 256-dim embedding (model `minishlab/potion-base-8M`) and versioned title/lede trigger flags. No chat-completion path in sweeps. A preview summary, if authorized by the user, is an optional *on-demand* local-model operation and must be labeled unavailable without Ollama; no fake fallback summary.

`fit(owner_labels_before_cutoff, features) -> PreferenceModel`: train only on that node's past labels; output probability or explicit `insufficient_labels` when classes are missing. Calibration needs held-out *training-window* folds and must not borrow the evaluation period. `score(item, owner_model) -> {preference, manipulation, feature_reasons, trigger_reasons}` with independent axes in `[0,1]`. Title/lede triggers are not a detector of factual falsity or ideological manipulation; reason codes describe measured features, not alleged motives.

`decide(item, rules, scores, peer_events, peer_weights, policy_version) -> {class, reasons, within_class_order, peer_contributions}`: evaluate hard rules first; local axes decide class; peers reorder **within** class under the proposed Article III policy. Every result has a nonempty `reasons` array, including cold-start and hard-rule cases. Within-class rank is derived at read time; no fused persisted score. Revoke/restore a peer recalculates rank immediately on this node only.

## Node → TypeScript JSON API

| Endpoint | Shape and effect |
|---|---|
| `GET /v1/inbox?class=allow\|digest\|block&cursor=...` | Cursor pagination of local items: ID, local title/lede/URL, class, separate scores, structured reason codes, weighted peer contributions. Suppressed items are queryable. |
| `POST /v1/labels` | `{item_id,vote:keep\|kill,mode:blind\|peers_visible\|relabel}`; writes local label and a **separately signed** vote event when the user chose sharing. Cannot write a peer's database. |
| `POST /v1/polls` | `{item_id}`; creates local poll and signs a `poll_invite` event; reject item not in this node's store. |
| `GET /v1/polls/{poll_id}` | Local aggregate only, with participants, missing/unknown peers, and each weight; label copy “your circle's take,” never “consensus.” |
| `POST /v1/peers/{author_id}/revoke` | Local toggle; old events auditable, weight zero immediately. |
| `GET /v1/health` | Local readiness only; no private model texts or peer keys. |

Each node gets its own port and DB; the UI node selector must be explicit, with current-node identity always visible to prevent mistaken voting. The UI must not synthesize a vote from a poll invitation. Typed TS DTOs are generated from the reviewed API contract (or kept in a single shared schema), rather than handwritten divergent copies. Do not expose the node API to remote browsers: browser same-origin/CORS must be restricted to the local UI origin.

## Eval report contract

A sweep consumes a pinned corpus checksum, frozen feature-cache/model version, five independently sourced human label files, a fixed time cutoff, predeclared arms, and seed. Report `{input_hashes, model_versions, seed, per_user_metrics, paired_deltas_with_ci, peer_visibility_effect, poison_top_k_exposure_ablation, limitations}`. Missing raters or blind relabels yield explicit `not_run` for dependent metrics — never synthesized observations. A deterministic synthetic five-persona **demo** report may prove wiring only and must be named `simulation`, not `evaluation`.
