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
  spec.md                            # requirements, threat model, eval design  <- you are here
  research.md                        # prior art, deltas, decision record D1-D5
  plan.md                            # (after ratification)
  data-model.md, contracts/, tasks.md
```

## Phase

**Spec ratification.** `spec.md` is DRAFT. `plan.md` and `tasks.md` are written only after the spec is
ratified and Q1–Q8 in `spec.md` §13 are resolved — spec errors are cheap to fix, plan errors are not.

Ratified decisions (2026-10-07): Python core + TypeScript web UI; 5-node demo **and** eval harness;
Ollama only; five local processes with their own SQLite over a filesystem/localhost bus; frozen fixture
for eval plus one live feed for the demo.
