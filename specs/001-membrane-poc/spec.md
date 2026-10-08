# Spec 001 — Membrane Agent POC

Status: **RATIFIED 2026-10-07** – ratified spec is frozen except by explicit amendment (with a version bump and a note here).
(with a version bump and a note here).
Version: 1.0.0 – ratified version.
Constitution: 1.2.0 – article references updated.
Research: `research.md` (prior art, decision record D1–D5, rejected alternatives).

---

## 1. Summary

A local-first curation membrane. Each node scores every inbound item on two orthogonal axes, learned
and tuned on that node only; a small trusted circle may contribute **signed votes keyed to
content-addressed item IDs — never bodies, never a global truth claim**; peer influence on the node's
gate is bounded, per-peer, revocable, and track-record-weighted; every decision carries a
human-readable reason. The POC's proof is a frozen-fixture experiment showing that peer signal moves
*accuracy* apart from mere *conformity*.

## 2. Problem

Feeds arriving at a person are ranked by whoever owns the ranking, optimizing engagement rather than
the reader's stated interest. The available defenses are solo filters (NewsBlur-class: they learn your
taste and therefore admit anything styled like your taste) or platform-global consensus artifacts
(Community Notes-class: powerful, but not yours, not private, and not calibrated to you). Nothing on
the market is *private, local, trust-scoped, with provenance*.

## 3. Goals

| ID | Goal |
|---|---|
| G1 | Five concurrent nodes, each with its own store, exchanging real signed votes over a local bus, each rendering a usable ranked inbox. |
| G2 | Demonstrate the novelty delta: solo+peer beats solo on held-out labels, **and** report influence and improvement separately so anchoring is visible rather than counted as value. |
| G3 | Show adversarial survivability at n=5: a poisoning peer's reach is capped, and the cap is ablatable so the damage of removing it is visible. |
| G4 | An honest privacy boundary that is asserted by test, not by claim: no body text, no rationale text, no scores leave the node. |

## 4. Non-goals

Not a recommender. Not a social network. Not global consensus. Not Sybil-resistant (identity is
out of scope; the bus is trusted transport and the *content* of votes is the untrusted surface).
No IMAP, no mobile, no hosting, no publishing, no moderation of third parties.

## 5. Scenarios

| ID | Scenario |
|---|---|
| S1 | **Cold start** — a node with zero labels becomes useful after a bounded onboarding pass. |
| S2 | **Triage** — the user works a ranked inbox; keep/kill actions persist and retrain the preference axis. |
| S3 | **Contested item** — user fires a one-click poll; peers vote; an advisory aggregate renders locally with per-peer weights. |
| S4 | **Poisoning peer** — one member floods and injects; measure how far it moves another node's inbox, cap on vs cap off. |
| S5 | **Revocation** — user revokes a peer mid-run; every subsequent item reflects exactly zero influence from it. |
| S6 | **Sweep** — a fixture run reproduces byte-identically and emits the baseline table. |

## 6. Threat model

| ID | Adversary | Capability | Requirement |
|---|---|---|---|
| A1 | Engagement-bait producer | High volume of low-value items | FR-5, FR-6 |
| A2 | In-group spoofer | Content styled in the user's register, engineered to capture attention | Art. II, FR-5, AC-2 |
| A3 | Poisoning peer | Floods votes, injects agenda items, forges another member's vote | Art. III, Art. IV, FR-8, FR-9, FR-10 |
| A4 | Upstream recommender | Ranks the source feed by dwell time | FR-1, FR-5 |
| A5 | The agent itself | Becomes an exfiltration surface | Art. I, Art. VIII, FR-9, AC-7 |

Explicitly **not** defended in this spec: Sybil identity, traffic analysis, host compromise,
coercion of a peer, and the user's own motivated reasoning. State these limits in the README so the
demo does not overclaim.

## 7. Functional requirements

### P1 — required for the POC to be the POC

**FR-1 Ingest.** One adapter interface; two implementations: fixture loader (JSONL) and live RSS
fetcher (single feed, demo only). Normalized output: `{item_id, title, body, url, source, fetched_ts}`.
*Acceptance:* both adapters satisfy the same interface contract test; ingest is idempotent by `item_id`.

**FR-2 Canonical item identity.** Two distinct jobs, deliberately not conflated:

- `item_id = H(normalize_url(url))` — the *same URL spelled differently*: tracking params
  (`utm_*`, `fbclid`, `gclid`, `ref`, `_hsenc`), AMP/mobile host and path variants, `http` vs
  `https`, fragments, trailing slashes, parameter order, default ports. URL-only, by design: the
  first draft folded the title into the id, which splits one story across several ids whenever a
  newsroom rewrites a headline — routine, and fatal to vote exchange.
- `content_key = simhash64(title x3, body x1)` — *different URL, same story*: syndication and
  cross-posting, compared by Hamming distance. The title carries triple weight because feed copies
  share the headline while truncating or padding the body.
- Grouping: same `item_id` **or** `hamming(content_key) <= d` (default `d = 3`), via a
  pigeonhole-banded union-find. Representative for a group: shortest normalized URL, then id —
  deterministic, so no node coordinates.

Reference implementation: `src/membrane/identity.py` (stdlib only, pure functions, no node state).
*Acceptance:* identical inputs produce identical `item_id` on all five nodes; `normalize_url` is
idempotent; banded grouping is verified equal to exhaustive all-pairs grouping on random data; a
headline rewrite does not change `item_id`; a truncated syndicated body stays inside the grouping
threshold (tests in `tests/test_identity.py`).

**FR-3 Local feature extraction.** Split by cost, per Art. VIII (1.1.0):
- *Corpus path (in-process, no chat LLM):* embeddings from a small local sentence model, plus
  deterministic lexical/structural features. Precomputed **once** into a cache keyed by `item_id` and
  read by all five nodes, so the sweep is bit-for-bit reproducible and five nodes never load five
  models into 6 GB of free RAM.
- *Interactive path (optional local server):* topical tags and a short neutral summary, generated
  on demand for items the user actually opens. Degrades gracefully to "no summary" when no local
  server is installed; never a per-item corpus cost.

*Acceptance:* no outbound call in the default path; identical fixture run yields identical features;
the sweep reports zero chat-completion calls; corpus-path feature extraction of the full fixture
completes well inside the §10 budget on the reference machine.

**FR-4 Preference scorer.** Per-node model trained on that node's keep/kill history; calibrated to
`[0,1]`; inspectable top-k contributing features. Must be usable after the S1 onboarding budget.
*Acceptance:* cold-start ranking after <= the Q2 label budget is materially better than random on
held-out labels; a scorer trained on node A's labels is not used by node B.

**FR-5 Manipulation scorer.** Separate model/feature set on the same item: curiosity-gap title
patterns, urgency/scarcity markers, outrage lexicon, CTA/listicle density, capitalization and
punctuation intensity, presence-bait phrasing. Freeze the feature list before the first sweep (Q8).
*Acceptance:* separate persisted value; no fused score exists (Art. II); AC-2 adversarial fixture passes.

**FR-6 Gate.** Deterministic order: hard rules -> local scores -> peer adjustment (reordering only within a verdict class). Emits `verdict ∈ {allow, digest, block}` plus a non‑empty reason set (Art. VI).
`verdict ∈ {allow, digest, block}` plus a non-empty reason set (Art. VI).
*Acceptance:* order is unit-tested; Art. III property test passes; FR-11 reasons always populated.

**FR-7 Inbox UI.** TypeScript web UI: ranked list, verdict, reason panel exposing matched rules /
top features / manipulation triggers / contributing peers with weights, keep/kill controls,
suppressed-items view, revocation control, poll control.
*Acceptance:* every displayed verdict can be traced to its reasons in <=2 clicks; UI renders 1k items
without degradation.

**FR-8 Vote log.** Append‑only per‑member signed log in the node's own SQLite: `(item_id, vote ∈ {keep,kill,abstain}, confidence, ts, author_id, seq, signature)`, ordered by per‑author monotonic `seq`.
{keep,kill,abstain}, confidence, ts, author_pubkey, sig)`, ordered by a vector clock.
*Acceptance:* tampering with any record fails verification on merge; forged authorship is rejected.
*Note:* this replaces the pitch's "CRDT-synced peer store" — see `research.md` §4.

**FR-9 Exchange bus.** Filesystem or localhost transport. Payload is exactly the FR-8 record shape —
no titles, no URLs, no bodies, no rationale, no scores (Art. I). Idempotent merge; malformed,
oversized, or unverifiable messages are quarantined and **fail closed** (do not degrade the gate
toward "allow").
*Acceptance:* AC-7 egress assertion; replaying the same batch twice changes nothing; a corrupted
batch leaves the inbox unchanged.

**FR-10 Trust.** Per-peer weight in `[0, cap]` derived from track record against the user's own later
labels, with recency decay and disuse decay; unidirectional (peer A's weight for you is independent of
your weight for A); revocable with immediate effect; never transitive.
*Acceptance:* Art. IV tests (a)(b)(c); S5 passes; per-peer contribution visible in FR-7.

**FR-11 Polls.** One‑click poll on a contested item → peer votes travel as FR‑8 records; poll invitations are `poll_invite` events with `poll_id`. No global write of any kind.
aggregate renders as an advisory card naming the circle and the participating weights. No global
write of any kind.
*Acceptance:* Art. V test (stopping one node leaves another's inbox byte-identical).

**FR-12 Eval harness.** Frozen-fixture sweep producing the §9 arms table, ablations, and confidence
intervals; fixed seed; byte-identical reruns.
*Acceptance:* two runs produce identical output hashes; sweep completes within the §10 budget.

**FR-13 Decision traces.** Per-decision structured trace exportable for the harness (which rule,
which features, which peers, what weights).
*Acceptance:* harness can attribute every arm delta to a component without re-running scorers.

### P2 — demo completeness

**FR-14 Live demo feed.** Single live RSS feed alongside the fixture corpus, clearly labeled as
unlabeled/non-evaluated. **FR-15** Onboarding flow (exemplar ranking + rule authoring). **FR-16**
Digest scheduling (batch the `digest` verdict by time window). **FR-17** Revocation and re-grant UI.

### P3 — explicitly deferred

Circle-level rollup lists (the only case that would genuinely need a CRDT). Multi-circle membership.
Federation across circles. Any shared mutable state between nodes.

## 8. Data requirements

- **Fixture corpus** — generated by a pinned, checksummed fetch script (raw bodies not committed
  unless Q4 clears licensing). Target 500–1500 items across a documented, mixed-quality feed list so
  that A1/A2 material exists in statistically useful quantity. **Requires accumulation over a capture
  window plus a per-source quota:** the first single pass produced 250 items, 72% of them from one
  bait-dense feed (research.md §8). Labeling a corpus that lopsided would measure the feed list
  rather than the membrane, and would skew every arm of §9.
- **Labels** — every corpus item labeled keep/kill by all five members; blind to peers' labels and to
  model output; a held-out split reserved by time so the sweep never trains on the eval window.
- **Inter-annotator agreement** — reported, not resolved. Disagreement is a first-class variable: it is
  what makes (a) the oracle arm meaningful and (b) the peer-signal arms non-trivial.
- **Adversarial fixtures** — hand-built: in-group-styled bait items (A2), a poison batch for FR-9, a
  forged-vote batch, and a known duplicate-group set for FR-2.
- **Live feed** — one feed for the demo; no labels; never enters the sweep.

## 9. Evaluation requirements

### 9.1 Arms (frozen fixture, held-out labels)

| Arm | Purpose |
|---|---|
| Random | floor |
| Heuristic (keyword/blocklist) | is the learned model earning its place? |
| Solo filter | the shipping prior art (NewsBlur-class) |
| Solo + peer votes | **the novelty delta (G2)** |
| Solo + peer votes + manipulation axis | **the adversarial delta (A2)** |
| 5-member majority | ceiling for this corpus; not a target to reach |

No values are pre-committed for these cells; the spec fixes the *instrument*, not the reading.

### 9.2 Metrics

- Precision / recall / AUC on held-out labels, per arm, with confidence intervals.
- **Noise blocked at a fixed budget** — at a fixed blocked fraction (default 30%), recall over items
  the user labeled kill, plus the false-block rate over items they labeled keep. Must be reported at a
  fixed budget or it is not comparable across arms.
- **Influence vs improvement (the headline).** Two-pass blind relabeling with a gap (Q5 fixes length):
  Arm A sees peer votes at vote time; Arm B votes blind. Report Δ agreement with peers (= influence)
  and Δ accuracy against the user's own later blind labels (= improvement). **Anchoring = agreement
  rises while accuracy does not.** These are reported together, always, never as one number.
- **Trust ablation.** `cap = 0` vs `cap = low` vs `cap = high` under A3 — does bounding cost accuracy
  against honest peers, and how much damage does it prevent from a hostile one?
- **Poisoning damage ratio.** Fraction of the victim's inbox a single adversarial peer can move, cap on
  vs off. The headline number for G3.
- **Spoofing resilience.** Block rate on the A2 fixture at high `preference`, manipulation axis on vs off.

### 9.3 Reproducibility

Fixed seed, frozen features, pinned corpus checksum. Reruns must be byte-identical (AC-8). Any change
to scorers, rules, gate order, or trust math requires a rerun (Art. VII).

## 10. Non-functional requirements

Local-first (Art. I, VIII). Deterministic scoring and sweep. Five concurrent processes on one machine.
Scoring latency target <= 2 s per item on the dev machine with cached embeddings; ingest of the full
fixture under 5 minutes. Crash-safe vote log — no loss or reordering on restart. Sweep wall-clock
target <= 10 minutes. No hidden network egress except the live feed fetch (FR-14), which is disabled
during sweeps.

**Reference machine (measured 2026-10-07).** Intel i7-8550U, 8 threads, no GPU, 15 GB RAM (~6 GB
available), 804 GB free disk, Python 3.12.3, Node 22.22.2. No Ollama, no ML packages installed. These
numbers set the §10 budgets and forced the FR-3 split: the in-process path fits the budget, per-item
chat-LLM extraction does not. First install must use CPU-only wheels
(`--index-url https://download.pytorch.org/whl/cpu`) — the default CUDA wheels are ~2.5 GB for a GPU
this machine does not have, against a 22 MB-class sentence model that actually does the work.

## 11. Out of scope

Section 4 non-goals, plus: P3 items, multi-circle membership, shared mutable state, mobile, hosting,
monetization, any notion of "immunity" (the corpus cannot demonstrate it and the claim is unfalsifiable
as stated).

## 12. POC acceptance criteria

| ID | Criterion |
|---|---|
| AC-1 | Five nodes run concurrently, each with its own SQLite, exchanging real signed votes over the local bus (FR-9). |
| AC-2 | Art. II adversarial fixture: in-group-styled bait at `preference >= 0.9` is gated when the manipulation axis is enabled and passes when it is not. |
| AC-3 | `item_id` agreement across nodes is 100% deterministic on the fixture; duplicate-group grouping meets the Q3 target. |
| AC‑4 | The solo+peer arm beats solo on held‑out AUC by a margin exceeding the fixture's label‑noise floor — **both numbers reported**; if it does not, that is the finding, not a failure to hide. |
| AC-5 | Influence and improvement are reported separately with CIs, and the anchoring gap is explicit (FR-12). |
| AC‑6 | With caps on, a single adversarial peer cannot move more than its cap‑weighted share of the victim's inbox; with caps off, the increased damage is demonstrated (FR‑10). |
| AC‑7 | No body, title, URL, score, or rationale text is observed on the bus in any run (Art. I). |
| AC-8 | Two sweeps of the frozen fixture produce identical output hashes (FR-12). |
| AC-9 | Every item in every verdict state carries a non-empty reason set (Art. VI). |
| AC-10 | The README's stated scope limits match §4/§6 — no overclaiming. |

## 13. Open questions (blocking `plan.md`)

| ID | Question | Why it blocks |
|---|---|---|
| Q1 | Exact trust-weight formula: agreement rate x recency decay x cap, and the information-free-peer rule (Art. IV(c)). | Determines FR-10 and the trust ablation design |
| Q2 | Onboarding protocol and label budget for cold start. | Determines FR-4 acceptance and S1 |
| Q3 | Duplicate detection: SimHash-64 is now implemented (`src/membrane/identity.py`) — what Hamming threshold and what fixture target accuracy? Default `d = 3`; measure the false-merge/false-split tradeoff on the known duplicate groups before freezing. | FR-2 acceptance (AC-3) |
| Q4 | Fixture feed list, capture window, licensing, commit-vs-fetch — **plus the fork measured in research.md §8: feed summaries are 94–272 chars, so the manipulation axis is title/lede-level unless article bodies are fetched (which adds per-host etiquette and licensing)**. | FR-1, FR-3, FR-5, §8 |
| Q5 | Label budget: items, raters per item, gap length for the conformity relabel, CI method. | §9.2 headline metric |
| Q6 | Live feed choice and refresh cadence. | FR-14 |
| Q7 | Does rationale text ever ship between peers? Default **no** (Art. I). Confirm. | Wire schema |
| Q8 | Manipulation feature list, frozen before the first sweep. | FR-5, comparability across runs |
| Q9 | Install Ollama at all, or defer the optional on-demand rationale path? The core corpus path is LLM-free either way. | FR-3 packaging; the target Art. VIII enforcement test points at |
