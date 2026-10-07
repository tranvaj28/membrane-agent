"""FR-2 — canonical item identity, shared verbatim by all five nodes.

Everything here is a pure function of the item's URL and text: no node-local state, no
configuration, no clock. That is what makes "the same item" agree across nodes (AC-3).

Two distinct jobs, deliberately not conflated:

* ``item_id``      — *same URL spelled differently* (tracking params, AMP variants, mobile
                     hosts, http/https, fragments). Depends on the URL **only**.
* ``content_key``  — *different URL, same story* (syndication, cross-posting). A 64-bit
                     SimHash over title + body, compared by Hamming distance.

Rejected design: ``item_id = H(url, title)`` (the first draft of spec FR-2). Newsrooms rewrite
headlines routinely — often minutes apart, and again for A/B tests — so folding the title into
the id splits one story into several ids and silently breaks vote exchange. The title instead
feeds ``content_key``, where a rewrite is a small edit rather than a new identity.

Stdlib only on purpose: this module runs on every node and is the contract plan.md documents.
The SimHash bit loop is O(tokens x 64) in pure Python (~15 s for a 1500-item corpus at import
time once); it is a one-off precompute and is cached, so it is not vectorised here.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

__all__ = [
    "ItemRef",
    "content_key",
    "group_duplicates",
    "hamming",
    "item_id",
    "normalize_text",
    "normalize_title",
    "normalize_url",
    "select_representative",
    "simhash64",
]

# Query parameters that identify the referrer or the campaign, never the document.
_TRACKING_PREFIXES = ("utm_", "pk_", "mc_", "hsa_", "oly_", "vero_", "elqtrack")
_TRACKING_EXACT = frozenset(
    {
        "fbclid", "gclid", "dclid", "gbraid", "wbraid", "yclid", "msclkid", "twclid",
        "igshid", "igsh", "ncid", "taid", "cmpid", "cmp", "campaign", "campaignid",
        "spm", "ref", "ref_src", "ref_url", "referrer", "source", "src", "trk",
        "trkcampaign", "wt_mc", "sc_cid", "_hsenc", "_hsmi", "_ga", "s", "si",
        "at_medium", "at_campaign", "siteid", "assetid", "assettype", "smid",
        "partner", "share_id", "sh", "__twitter_impression",
    }
)
# Hostname prefixes that serve the same document as the bare host.
_HOST_PREFIXES = ("www.", "m.", "amp.", "amp-", "mobile.", "touch.", "amp")
# Path suffixes that serve the same document under an AMP/mobile renderer.
_AMP_SUFFIXES = ("/amp.html", ".amp.html", "/amp/", "/amp", "/mobile/", "/mobile")
_DEFAULT_PORTS = {"http": "80", "https": "443"}
_SCHEMES = ("http", "https")

_WORD_SPLIT = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class ItemRef:
    """Minimal handle needed for grouping. ``content_key`` is the 64-bit SimHash."""

    item_id: str
    url: str
    title: str
    content_key: int


def _strip_host_prefixes(host: str) -> str:
    changed = True
    while changed:
        changed = False
        for prefix in _HOST_PREFIXES:
            if host.startswith(prefix) and len(host) > len(prefix):
                remainder = host[len(prefix) :]
                # Never reduce a host to nothing, and never eat a real label such as
                # "amp.com" or "m.tv" — a bare host must keep at least one dot.
                if "." in remainder:
                    host = remainder
                    changed = True
                break
    return host


def normalize_url(url: str) -> str:
    """Return the canonical form of ``url``; ``""`` for anything unusable.

    Deterministic and idempotent: ``normalize_url(normalize_url(u)) == normalize_url(u)``.
    """
    url = (url or "").strip()
    if not url:
        return ""

    parts = urlsplit(url)
    # Scheme-less absolute form, e.g. "example.com/a" (common in hand-written fixtures).
    if not parts.netloc and parts.path and not parts.path.startswith("/"):
        head = parts.path.split("/", 1)[0]
        if "." in head:
            parts = urlsplit("//" + url)

    scheme = (parts.scheme or "").lower()
    if scheme not in _SCHEMES:
        scheme = "https" if scheme == "" else scheme

    host = (parts.netloc or "").lower()
    if "@" in host:  # credentials carry no identity
        host = host.rsplit("@", 1)[1]
    if ":" in host:
        name, _, port = host.rpartition(":")
        if port == _DEFAULT_PORTS.get(scheme):
            host = name
    host = _strip_host_prefixes(host)

    path = parts.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    lowered = path.lower()
    for suffix in _AMP_SUFFIXES:
        if lowered.endswith(suffix) and len(lowered) > len(suffix):
            path = path[: -len(suffix)] or "/"
            lowered = path.lower()
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    kept: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith(_TRACKING_PREFIXES) or key_lower in _TRACKING_EXACT:
            continue
        if key_lower in {"amp", "output"} and value.lower() in {"1", "amp", "true"}:
            continue
        kept.append((key_lower, value))
    kept.sort()

    if not host:
        # Not an HTTP document (or unparseable): fall back to path+query under the scheme.
        return urlunsplit((scheme, "", path, urlencode(kept), ""))

    # http and https serve the same document; pick https so the two collapse.
    return urlunsplit(("https", host, path, urlencode(kept), ""))


def normalize_text(text: str) -> str:
    """NFKC, case-folded, alphanumeric-only, single-spaced. Unicode-aware (no ASCII ranges)."""
    if not text:
        return ""
    folded = unicodedata.normalize("NFKC", text).casefold()
    keep = [ch if ch.isalnum() else " " for ch in folded]
    return _WORD_SPLIT.sub(" ", "".join(keep)).strip()


def normalize_title(title: str) -> str:
    """Titles get the same treatment as body text; kept separate for call-site clarity."""
    return normalize_text(title)


def item_id(url: str, title: str = "") -> str:
    """Stable 16-hex identity for a document.

    URL-dominant by design (see module docstring). Falls back to the title only when the URL is
    unusable, so link-less feed entries still get a deterministic identity.
    """
    normalized = normalize_url(url)
    if normalized:
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    normalized_title = normalize_title(title)
    if normalized_title:
        return hashlib.sha256(("title:" + normalized_title).encode("utf-8")).hexdigest()[:16]
    return ""


def _tokens(text: str) -> list[str]:
    """Word unigrams plus bigrams — bigrams give short titles some word-order signal."""
    words = normalize_text(text).split()
    if len(words) < 3:
        return words
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def _simhash_from_counts(counts: Counter[str]) -> int:
    if not counts:
        return 0
    vector = [0] * 64
    for token, weight in counts.items():
        digest = int.from_bytes(
            hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big"
        )
        for bit in range(64):
            vector[bit] += weight if (digest >> bit) & 1 else -weight
    result = 0
    for bit, total in enumerate(vector):
        if total > 0:
            result |= 1 << bit
    return result


def simhash64(text: str) -> int:
    """Unweighted SimHash of ``text``; used directly in tests and for body-only keys."""
    return _simhash_from_counts(Counter(_tokens(text)))


def content_key(title: str, body: str = "") -> int:
    """Weighted SimHash: title counts triple, body counts once.

    The weighting is the syndication defence: feed copies routinely carry the same headline with
    a truncated or padded summary, so the invariant part must dominate the key.
    """
    counts: Counter[str] = Counter(_tokens(title))
    for token in _tokens(title):
        counts[token] += 2
    counts.update(_tokens(body))
    return _simhash_from_counts(counts)


def hamming(left: int, right: int) -> int:
    """Bit distance between two SimHashes."""
    return (left ^ right).bit_count()


class _DisjointSet:
    __slots__ = ("parent",)

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, index: int) -> int:
        parent = self.parent
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(self, left: int, right: int) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[max(root_left, root_right)] = min(root_left, root_right)


def group_duplicates(refs: Iterable[ItemRef], max_distance: int = 3) -> list[list[str]]:
    """Group items that are the same document, by identical ``item_id`` or close ``content_key``.

    Candidate pairs are found by banding the 64-bit key into ``max_distance + 1`` bands: if two
    keys differ in at most ``max_distance`` bits, at least one band is identical (pigeonhole), so
    no true pair is missed. That keeps the grouping near-linear instead of O(n^2) over ~10^6 pairs.

    Returns groups of ``item_id``s, sorted by first member; singletons are included.
    """
    items = list(refs)
    if not items:
        return []

    dsu = _DisjointSet(len(items))

    first_seen: dict[str, int] = {}
    for index, ref in enumerate(items):
        previous = first_seen.get(ref.item_id)
        if previous is None:
            first_seen[ref.item_id] = index
        else:
            dsu.union(previous, index)

    bands = max(1, max_distance + 1)
    width = max(1, 64 // bands)
    mask = (1 << width) - 1
    buckets: dict[tuple[int, int], list[int]] = {}
    for index, ref in enumerate(items):
        for band in range(bands):
            buckets.setdefault((band, (ref.content_key >> (band * width)) & mask), []).append(index)

    for candidates in buckets.values():
        if len(candidates) < 2:
            continue
        for left_pos, left in enumerate(candidates):
            for right in candidates[left_pos + 1 :]:
                if dsu.find(left) == dsu.find(right):
                    continue
                if hamming(items[left].content_key, items[right].content_key) <= max_distance:
                    dsu.union(left, right)

    merged: dict[int, set[str]] = {}
    for index, ref in enumerate(items):
        merged.setdefault(dsu.find(index), set()).add(ref.item_id)

    groups = [sorted(ids) for ids in merged.values()]
    groups.sort(key=lambda group: group[0])
    return groups


def select_representative(refs: Sequence[ItemRef], group: Sequence[str]) -> str:
    """Canonical ``item_id`` for a duplicate group: shortest normalized URL, then id.

    Deterministic, so every node picks the same representative for a syndicated story without
    coordinating.
    """
    members = [ref for ref in refs if ref.item_id in set(group)]
    if not members:
        return ""
    members.sort(key=lambda ref: (len(normalize_url(ref.url)), ref.item_id))
    return members[0].item_id
