# Membrane POC Constitution

Version: 1.2.0
Ratified: 2026-10-07; amended to 1.1.0 the same day (Art. VIII wording — see Amendment record)
Scope: every spec under `specs/`. This document outranks specs and plans.

The project's only defensible claim is *a private, trust-scoped curation membrane you own*.
Each article below exists to protect that claim from a specific, named way it degrades into a
worse version of products that already exist (see `specs/001-membrane-poc/research.md`).
A change that cannot satisfy an article requires a constitution amendment — not a spec exception.

---

## I. Body text never crosses the wire

**Rule.** The only inter-node payload is `(item_id, vote, confidence, ts, sig)`. Titles, URLs,
bodies, embeddings, summaries, scores, and rationale text stay on the node that observed them.

**Rationale.** Local-first is the product's only non-replicable property; "no bodies leave the
machine" is checkable and true, whereas "we won't read them" is not. Pyzor/Razor established that
collaborative unwanted-content signaling works on digests alone (`https://www.pyzor.org/en/latest/about.html`).

**Enforcement.** `contracts/vote-log.schema.json` has no free-text field. A fixture test asserts
every exchanged record validates against it. An egress test asserts bus traffic contains no body
substring from the fixture corpus.

---

## II. Two axes, never collapsed

**Rule.** `preference` ("do I want this?") and `manipulation` ("is this engineered to make me want
it?") are stored, tuned, reported, and gated separately. No code path may persist a single fused score.

**Rationale.** A filter trained on your own values admits anything styled like your in-group — that is
precisely the attack the membrane is supposed to stop. A preference-only filter is trivially spoofable
by construction.

**Enforcement.** Data-model test: no table or DTO exposes a fused scalar. Adversarial fixture: an item
written in the user's in-group register with bait markers must be gated even at `preference >= 0.9`
when `manipulation >= threshold`.

---

## III. Hard rules are sovereign

**Rule.** Evaluation order is fixed: (1) hard rules, (2) local scores, (3) peer adjustment. Peer
adjustment may reorder items inside a verdict class and may never promote an item out of one.

**Rationale.** Without this, a poisoning peer is effectively your editor.

**Enforcement.** Gating-order unit test. Property test: for any peer-vote set, an item matching an
allow or block rule has an unchanged verdict class.

---

## IV. Peer influence is bounded, per-peer, unidirectional, revocable

**Rule.** Weight per peer lies in `[0, cap]`, derives only from that peer's track record against your
own later labels, decays with disuse, is never transitive, and takes effect immediately on revocation
for all future items.

**Rationale.** Levien & Aiken's capacity argument: a bounded flow soaks up an attacker's capacity, so
the damage a bad peer can do is capped a priori rather than detected after the fact
(`https://theory.stanford.edu/~aiken/publications/papers/usenix97.pdf`).

**Enforcement.** Trust unit tests: (a) a peer that always agrees never exceeds `cap`; (b) a revoked
peer contributes exactly `0`; (c) a peer voting identically on every item gains no weight (no
information → no influence).

---

## V. Verdicts are advisory, never global truth

**Rule.** No component persists or displays a peer aggregate as a factual claim. There is no
cross-node shared store: each membrane's verdict lives only in that node's SQLite and UI, and the UI
copy says whose circle's take it is.

**Rationale.** With five peers, a majority is "whoever is online". Community Notes needs >=5 ratings
*and* hundreds of raters because bridging across cliques is what buys manipulation resistance
(`https://communitynotes.x.com/guide/en/under-the-hood/ranking-notes`). At n=5 the honest artifact is
advice, not consensus.

**Enforcement.** No write path exists outside the node's own database. Test: stopping node A leaves
node B's inbox byte-identical.

---

## VI. Every decision is explainable

**Rule.** Each item carries a non-empty reason set: matched rules, top-k preference features,
manipulation triggers, and contributing peers with weights. Suppressed items remain queryable. There
are no silent drops.

**Rationale.** "Your own stated values" is marketing unless the user can inspect what the membrane did
and why. The eval harness also attributes deltas through these reasons.

**Enforcement.** API contract test: `reasons` is non-empty for every item in every verdict state.

---

## VII. Eval-gated changes

**Rule.** Any change to scorers, rules, gating, or trust math must produce a sweep report against the
frozen fixture, with deltas against the declared baselines. No merge without the numbers.

**Rationale.** This POC's deliverable is a falsifiable result, not a demo that merely runs.

**Enforcement.** `make eval` target; PR/review template requires the baseline table.

---

## VIII. Local inference only

**Rule.** The default path performs no outbound model API call. All inference runs on the local
machine: in-process models (embeddings, classical classifiers, deterministic feature extractors) on
the corpus path, and a local model server (Ollama, when installed) for on-demand rationale generation.
No sweep pass may depend on a chat-LLM call per item.

**Rationale.** Article I is worthless if the body is POSTed to a hosted model to be scored. The
corpus-path restriction is also a capacity argument: on the reference machine (8-thread CPU, no GPU,
6 GB free RAM) a 7B chat model costs on the order of 5–15 s per item, putting a 1000-item x 6-arm
sweep out of reach, while the embedding + lexicon path completes in seconds and is bit-for-bit
deterministic. See `specs/001-membrane-poc/research.md` §6.

**Enforcement.** Config default plus an integration test that fails if a hosted provider is reachable
in the default path; egress assertion during the sweep; a sweep-time assertion that the run performed
zero chat-completion calls.

---

## Governance

Amendments bump the version, state the article affected, and record the reason in
`specs/*/research.md`. Specs cite articles by number. Where a spec and this document conflict,
this document wins.

## Amendment record

| Version | Article | Reason |
|---|---|---|
| 1.1.0 | VIII | 1.0.0 named "a local Ollama endpoint" as the only permitted inference path. Probing the reference machine found no Ollama installed and CPU-only hardware, where per-item chat-LLM extraction cannot meet the eval budget. Reworded to *local inference, in-process models on the corpus path, local server for on-demand rationale*, and added the no-per-item-chat-LLM sweep assertion. Privacy intent unchanged; cost model corrected. See `specs/001-membrane-poc/research.md` §6. |
| 1.2.0 | I | Add bounded protocol metadata (`version`, `kind`, `author_id`, `seq`, `poll_id`). Keep fixture cache shared read‑only; live embeddings per‑node. |
| 1.2.0 | V | Change inbox‑identical test: A has no write access to B's SQLite; after stopping A, B changes only via its own ingest or processing already‑received signed events. |
| 1.2.0 | VIII | Ollama not installed; no on‑demand generation; deterministic reason codes; never fake LLM summary. |
