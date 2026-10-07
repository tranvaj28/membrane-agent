# Research — Membrane Agent POC

Feeds `spec.md`. Records what already exists, what is actually left to prove, and the decisions this
spec is built on. Source material for the idea itself: `/tmp/ideas/all.json:646-654` (EP 337,
Philip Rosedale, 2026-03-27), quotes attributed to Jim Rutt and Rosedale.

> Note on provenance: the local `ideas/pages/ep-337-*.html` files are paywalled shells with no
> transcript body, so the surrounding argument could not be read — only the extracted quotes. If the
> full segment is available elsewhere, re-check §"Threat model basis" before ratifying.

---

## 1. Prior art, and what is actually left

| Component of the idea | Status | Prior art | Delta left for us |
|---|---|---|---|
| Filter inbound items against your stated values; learn from keep/kill | **Shipped** | NewsBlur Intelligence Training — thumbs up/down on author, tag, title, keyword; per-classifier; "You're in control, not an algorithm" (`https://dev.newsblur.com/features/intelligence-training`); Bayesian spam filtering (2002–) | None on its own. This is the floor, not the contribution. |
| Poll peers on an item → a verdict attached to that item | **Shipped at scale** | Community Notes: notes stay "Needs More Ratings" until >=5 ratings, then bridging-based matrix factorization decides Helpful / Not Helpful (`https://communitynotes.x.com/guide/en/under-the-hood/ranking-notes`, `https://github.com/twitter/communitynotes/tree/main/scoring/src/scoring/matrix_factorization`) | Ours is *per-membrane* and advisory, not one platform-global truth claim. |
| Exchange peer signals about items without sharing the items | **Solved primitive** | Pyzor/Razor — "collaborative, networked system to detect and block spam using identifying **digests** of messages" (`https://www.pyzor.org/en/latest/introduction.html`) | Adopt wholesale. Confirms Article I is a solved wire format, not a research risk. |
| Bound a peer's influence so a bad actor cannot capture you | **Solved theory** | Levien & Aiken, attack-resistant trust metrics; Advogato capacity-bounded maxflow (`https://theory.stanford.edu/~aiken/publications/papers/usenix97.pdf`, `http://www.levien.com/thesis/compact.pdf`) | Adopt the capacity model; the POC's job is to *show* it at n=5. |
| Manipulation / engineered-attention scoring as a distinct axis | Partially shipped | Clickbait detection literature; platform-internal classifiers | Not shipped as a user-owned, separately-tunable axis alongside their own preference model. |

**Residual novelty, stated narrowly:** a *per-membrane, trust-scoped verdict* over content-addressed
items — private, locally owned, with provenance and reasons — that informs your default instead of
asserting global truth; plus the evaluation that separates **influence** from **improvement**.

Everything else in the pitch is either prior art or framing.

---

## 2. Threat model basis

Rutt's framing is explicitly defensive — the agent exists because "these kinds of plays" get through.
A spec with no adversary produces a demo that cannot be defended. Adversaries carried into `spec.md` §6:

- **A1** high-volume engagement bait (volume + bait patterns)
- **A2** in-group-styled spoofing (content written in the user's register) — defeats a values-trained
  preference filter *by construction*, which is why Constitution Article II exists
- **A3** poisoning peer (flooding, agenda injection, forged votes) — Constitution Articles III + IV
- **A4** the upstream recommender optimizing dwell time rather than the user's stated interest
- **A5** the agent itself as a new exfiltration surface — Constitution Articles I + VIII

**Known scaling limit, stated up front:** community-note-style consensus needs far more than five
raters to be manipulation-resistant. This POC therefore does not claim consensus at n=5; it claims
trust-weighted signal propagation and measures its calibration. See `spec.md` §9.

---

## 3. Decision record

Ratified by the user, 2026-10-07:

| # | Decision | Choice | Consequence |
|---|---|---|---|
| D1 | Runtime | **Python core + TypeScript web UI** | Scorer/eval in Python; two build surfaces, one contract boundary |
| D2 | POC gate | **5-node demo + eval harness** | Both must exist; neither alone closes the spec |
| D3 | Model policy | **Ollama only** | Article VIII enforced by default; feature extraction must be local and fast enough to matter |
| D4 | Peer transport | **5 local processes, own SQLite each, filesystem/localhost bus** | Keeps real serialization, item-identity, and signature bugs in scope; preserves reproducibility |
| D5 | Corpus | **Frozen fixture for eval + one live RSS feed for demo** | Sweep is reproducible and falsifiable; demo shows real friction |

---

## 4. Alternatives considered and rejected

| Rejected | Why |
|---|---|
| In-process simulated peers | Hides exactly the engineering worth proving (identity agreement, serialization, forgery, ordering) |
| CRDT peer store | CRDTs solve concurrent *mutable* state. Votes are immutable appends: an append-only per-member signed log with a vector clock is sufficient and much smaller |
| IMAP ingestion for the POC | Adds auth, MIME, threading, and a privacy footprint that contradicts Articles I and VIII — for zero novelty. Keep the adapter interface; implement RSS + fixture only |
| Real network / peer discovery | NAT, key distribution, and latency for no additional proof; kills byte-identical reproducibility |
| Single fused score | Violates Article II; collapses the one axis that resists spoofing |
| "How much noise was blocked" as the headline metric | Not falsifiable without a baseline; measures influence, not value. Replaced by the arms table in `spec.md` §9 |
| API-backed LLM scoring | Violates Articles I and VIII |

---

## 5. Open questions — must be resolved before `plan.md` is written

Carried as Q1–Q8 in `spec.md` §13. Ranking by blocking power:

1. **Q1 trust-weight formula** — agreement rate x recency decay x cap; needs exact form and the
   information-free-peer rule (Article IV(c)).
2. **Q5 label budget** — how many items, how many raters per item, blind protocol, gap length for the
   conformity re-label.
3. **Q4 fixture source list** — feed list, capture window, licensing, and whether raw bodies may be
   committed or must be fetched by a pinned-checksum script.
4. **Q3 duplicate detection** — simhash vs embedding cosine threshold, and the target accuracy on the
   fixture's known duplicate groups.
5. **Q8 manipulation feature list** — freeze before first sweep, or the baseline table is not comparable
   across runs.
