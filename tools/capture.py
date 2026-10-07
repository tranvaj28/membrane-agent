#!/usr/bin/env python3
"""FR-1 — capture the frozen fixture corpus (metadata + feed-provided summary).

Usage:
    PYTHONPATH=src .venv/bin/python tools/capture.py [--per-feed N] [--limit N]

Two deliberate properties:

* ``fetched_ts`` is written to ``capture_meta.json``, never into ``corpus.jsonl``, so a re-capture
  of the same window is byte-identical and the sweep stays reproducible (spec AC-8).
* Feed bodies come from the feed itself (``entry.summary``/``content``). Article scraping is out
  of scope for the POC: it adds per-host etiquette and licensing questions for no eval value.
  ``--fetch-bodies`` is intentionally absent until Q4 is answered.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from membrane.identity import ItemRef, content_key, group_duplicates, item_id  # noqa: E402

USER_AGENT = "membrane-poc/0.0.1 (+local research prototype; respects robots)"
MAX_BODY_CHARS = 4000


def load_feeds(path: Path) -> list[dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    feeds = data.get("feeds") or []
    if not feeds:
        raise SystemExit(f"no feeds configured in {path}")
    return feeds


def parse_entry(entry: dict, feed: dict[str, str]) -> dict[str, str] | None:
    link = (entry.get("link") or "").strip()
    title = (entry.get("title") or "").strip()
    identifier = item_id(link, title)
    if not identifier:
        return None

    body = (entry.get("summary") or "").strip()
    if not body:
        contents = entry.get("content") or []
        if contents:
            body = (contents[0].get("value") or "").strip()
    body = body[:MAX_BODY_CHARS]

    published = (entry.get("published") or entry.get("updated") or "").strip()
    return {
        "item_id": identifier,
        "url": link,
        "title": title,
        "source": feed["name"],
        "feed_url": feed["url"],
        "published": published,
        "author": (entry.get("author") or "").strip(),
        "summary": body,
        "content_key": f"{content_key(title, body):016x}",
    }


def fetch_feed(client: httpx.Client, feed: dict[str, str], per_feed: int) -> tuple[list[dict], str]:
    try:
        response = client.get(feed["url"])
        response.raise_for_status()
    except httpx.HTTPError as error:  # a dead feed must not abort the capture
        return [], f"error: {type(error).__name__}: {error}"

    parsed = feedparser.parse(response.content)
    records: list[dict[str, str]] = []
    for entry in parsed.entries:
        record = parse_entry(entry, feed)
        if record is not None:
            records.append(record)
        if per_feed and len(records) >= per_feed:
            break
    return records, "ok" if records else "empty"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feeds", default=str(ROOT / "fixtures" / "feeds.yaml"))
    parser.add_argument("--out", default=str(ROOT / "fixtures" / "corpus.jsonl"))
    parser.add_argument("--groups", default=str(ROOT / "fixtures" / "corpus_groups.json"))
    parser.add_argument("--meta", default=str(ROOT / "fixtures" / "capture_meta.json"))
    parser.add_argument("--per-feed", type=int, default=0, help="cap entries per feed (0 = all)")
    parser.add_argument("--limit", type=int, default=0, help="cap total curated items (0 = all)")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    feeds = load_feeds(Path(args.feeds))
    statuses: list[dict[str, object]] = []
    records: list[dict[str, str]] = []

    with httpx.Client(
        timeout=args.timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for feed in feeds:
            fetched, status = fetch_feed(client, feed, args.per_feed)
            statuses.append({"name": feed["name"], "url": feed["url"], "status": status, "raw": len(fetched)})
            records.extend(fetched)

    # Deduplicate by item_id, keeping the first sighting in stable sort order.
    records.sort(key=lambda record: (record["source"], record["published"], record["item_id"]))
    unique: dict[str, dict[str, str]] = {}
    for record in records:
        unique.setdefault(record["item_id"], record)
    curated = list(unique.values())
    if args.limit:
        curated = curated[: args.limit]

    refs = [
        ItemRef(record["item_id"], record["url"], record["title"], int(record["content_key"], 16))
        for record in curated
    ]
    groups = [group for group in group_duplicates(refs, max_distance=3) if len(group) > 1]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for record in curated:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    Path(args.groups).write_text(
        json.dumps({"max_distance": 3, "duplicate_groups": groups}, indent=2), encoding="utf-8"
    )

    per_source: dict[str, int] = {}
    for record in curated:
        per_source[record["source"]] = per_source.get(record["source"], 0) + 1

    Path(args.meta).write_text(
        json.dumps(
            {
                "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "per_feed": statuses,
                "totals": {
                    "raw_entries": len(records),
                    "unique_items": len(curated),
                    "duplicate_groups": len(groups),
                    "largest_group": max((len(group) for group in groups), default=1),
                },
                "per_source": per_source,
                "max_body_chars": MAX_BODY_CHARS,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"corpus: {len(curated)} unique items -> {out_path}")
    print(f"per-source: {json.dumps(per_source, sort_keys=True)}")
    print(
        f"duplicate groups (>1): {len(groups)}, largest {max((len(g) for g in groups), default=1)}"
    )
    for status in statuses:
        print(f"  feed {status['name']:24} {status['status']:6} raw={status['raw']}")
    if len(curated) < 200:
        print("WARNING: corpus is small; widen the feed list or drop --per-feed before labeling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
