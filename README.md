# Membrane POC

A local-first curation membrane: every inbound item is scored on two orthogonal axes (want /
manipulative), scored on your own machine; a small trusted circle may contribute signed votes keyed to
content-addressed item IDs — never bodies, never a global truth claim — and peer influence on your gate
is bounded, per-peer, revocable, and track-record-weighted. Every decision carries a reason.

Source of the idea: `/tmp/ideas/all.json:646-654` (EP 337, Philip Rosedale, 2026-03-27).

## Scope limits (do not overclaim in the demo)

Not defended: Sybil identity, traffic analysis, host compromise, coercion of a peer, the user's own
motivated reasoning. Not claimed: immunity to manipulation; consensus — with five peers a majority is
"whoever is online", so peer output is *advisory* and its value is measured, not assumed.

Critically: the shipped prior art is a solo preference filter (NewsBlur Intelligence Training) and a
platform-global peer poll (Community Notes). The claim under test here is narrow — see
`specs/001-membrane-poc/research.md` §1.

## Spec-driven layout

```
.specify/memory/constitution.md      # 8 invariants; outranks specs
specs/001-membrane-poc/
  spec.md                            # DRAFT requirements and acceptance criteria
  research.md                        # prior art, measured probes, decision record D1–D5
  plan.md                            # PROPOSED architecture; pending user corrections
  data-model.md                      # PROPOSED node-local storage
  contracts/                         # PROPOSED event, exchange and classifier interfaces
  tasks.md                           # not written; post-approval phase
```

## Phase

**Planning review.** `spec.md` remains DRAFT; `plan.md`, `data-model.md` and `contracts/` are
proposals, not ratification or permission to implement. The adversarial reviewer is paused until the
user selects its model. `tasks.md` and all runtime implementation are held until corrections and
explicit go-ahead. Planning gate P1 requires an Article I amendment before any event code may ship;
see `plan.md` §2 for the other decisions and `spec.md` §13 for Q1–Q9.

User-selected direction (2026-10-07): Python core + TypeScript web UI; 5-node demo **and** eval harness;
Ollama-only local inference; five local processes with their own SQLite over a filesystem/localhost bus;
frozen fixture for eval plus one live feed for the demo. The D3 amendment in `research.md` §6
proposes a local in-process corpus path with optional Ollama; that change still requires user
approval at plan gate P6.
