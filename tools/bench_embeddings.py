#!/usr/bin/env python3
"""Reference-machine budget evidence for spec §10 / constitution Art. VIII (1.1.0).

Answers one question with numbers instead of prediction: can the corpus path (embedding + classical
features, no chat LLM) stay inside the sweep budget on a GPU-less 8-thread laptop?

Run: PYTHONPATH=src .venv/bin/python tools/bench_embeddings.py [--items N]
Reads fixtures/corpus.jsonl when present, otherwise builds synthetic items from a fixed wordlist so
the benchmark is runnable before the corpus exists.
"""

from __future__ import annotations

import argparse
import json
import random
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_MODEL = "minishlab/potion-base-8M"
WORDS = (
    "central bank rates inflation market quarter earnings report storm warning coast election "
    "senate vote policy energy grid chip factory launch update study researchers climate data "
    "shares index trading deal merger regulator probe outage service platform users privacy"
).split()


def load_texts(limit: int) -> tuple[list[str], str]:
    corpus = ROOT / "fixtures" / "corpus.jsonl"
    if corpus.exists():
        texts: list[str] = []
        with corpus.open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                texts.append(f"{record.get('title', '')} {record.get('summary', '')}".strip())
                if limit and len(texts) >= limit:
                    break
        if texts:
            return texts, f"fixtures/corpus.jsonl ({len(texts)} items)"
    rng = random.Random(11)
    size = limit or 1000
    return [" ".join(rng.choices(WORDS, k=40)) for _ in range(size)], f"synthetic ({size} items)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, default=0, help="cap items (0 = all)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    from model2vec import StaticModel  # imported late so --help stays fast

    texts, provenance = load_texts(args.items)
    print(f"items: {provenance}")

    started = time.perf_counter()
    model = StaticModel.from_pretrained(args.model)
    load_seconds = time.perf_counter() - started

    started = time.perf_counter()
    first = model.encode(texts)
    first_seconds = time.perf_counter() - started

    started = time.perf_counter()
    second = model.encode(texts)
    second_seconds = time.perf_counter() - started

    identical = bool((first == second).all())
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    dim = first.shape[1]

    print(f"model load      : {load_seconds:.2f} s")
    print(f"encode pass 1   : {first_seconds:.2f} s ({len(texts) / max(first_seconds, 1e-9):.0f} items/s)")
    print(f"encode pass 2   : {second_seconds:.2f} s")
    print(f"deterministic   : {identical}")
    print(f"embedding dim   : {dim}")
    print(f"peak RSS        : {peak_mb:.0f} MB")

    if not identical:
        print("FAIL: encode() is not bit-reproducible; AC-8 cannot hold with this backend")
        return 1
    if len(texts) / max(first_seconds, 1e-9) < 50:
        print("FAIL: corpus-path throughput cannot meet the §10 sweep budget")
        return 1
    print("OK: corpus path is CPU-feasible and bit-reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
