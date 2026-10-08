# Tasks for Spec 001 – Membrane Agent POC (v1.0.0)

**Links:**
- Spec: `spec.md`
- Plan: `plan.md`
- Data model: `data-model.md`
- Contracts: `contracts/vote-log.schema.json`, `contracts/exchange.md`, `contracts/classifier.md`

## Legend
- `[P]` parallelizable (different files, no dependency)

## Tasks
### Phase 0 – Setup
- **T001** `[P]` Install Python dependencies (model2vec, scikit‑learn, numpy, feedparser, pynacl, jsonschema, pytest) as declared in `pyproject.toml`.
- **T002** `[P]` Generate fixture cache: run `tools/bench_embeddings.py` on the frozen RSS fixture to produce the shared read‑only cache.

### Phase 1 – Foundations
- **T101** `src/membrane/identity.py` – Verify `item_id` generation matches Constitution I (URL‑only) and `content_key` hashing.
  - **FR‑2**
- **T102** `data-model.md` – Apply SQLite schema migrations for tables `items`, `item_groups`, `features`, `labels`, `rules`, `peers`, `events`, `event_conflicts`, `polls`, `verdicts`, `captures`.
  - **FR‑2**, **FR‑10**, **FR‑8**, **FR‑11**
- **T103** `contracts/vote-log.schema.json` – Update title/description to reference Constitution I v1.2.0.
  - **FR‑8**, **FR‑9**
- **T104** `contracts/exchange.md` – Ensure schema matches per‑author `seq` ordering and `poll_invite` kind.
  - **FR‑9**, **FR‑11**

### Phase 2 – Scorers & Gate
- **T201** `src/membrane/scorer.py` – Implement Preference scorer returning `[0,1]` and exposing top‑k feature reasons.
  - **FR‑4**, **FR‑6**, **VI**
- **T202** `src/membrane/manipulation.py` – Implement Manipulation scorer with frozen feature list (see `contracts/classifier.md`).
  - **FR‑5**, **II**
- **T203** `src/membrane/gate.py` – Apply hard‑rule → preference → manipulation → peer‑adjustment ordering; enforce no cross‑class reordering (Article III).
  - **FR‑6**, **III**

### Phase 3 – Peer‑trust & Polls
- **T301** `src/membrane/trust.py` – Compute per‑peer weight `w = min(0.25, 0.25·J·2^{‑idle_days/30})` using Youden‑J formula, decay, and revocation handling.
  - **FR‑10**, **IV**
- **T302** `src/membrane/poll.py` – Create poll invitation (`kind="poll_invite"`) and poll response handling; ensure `poll_id` inclusion.
  - **FR‑11**, **V**

### Phase 4 – Evaluation Harness
- **T401** `tools/eval_harness.py` – Run frozen‑fixture sweep, generate arms table, produce deterministic hashes for AC‑8.
  - **FR‑12**, **VIII**, **AC‑8**
- **T402** `tests/test_evaluation.py` – Verify AC‑1 through AC‑10 automatically; include leave‑one‑out baseline for AC‑4.

### Phase 5 – Documentation & Cleanup
- **T501** `README.md` – Update Phase section to "Tasks. Spec 001 ratified 2026‑10‑07; implementation awaits user go‑ahead." and replace Ollama mention with Art VIII outcome.
  - **IV**, **VIII**
- **T502** `plan.md` – Change status to **APPROVED** and update heading to "Decision gates (resolved 2026‑10‑07)".
  - **P1‑P7** resolved

All tasks are small, verifiable, and have no placeholders.
