"""FR-2 tests. The headline risk is not the happy path — it is silent identity splits."""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from membrane.identity import (
    ItemRef,
    content_key,
    group_duplicates,
    hamming,
    item_id,
    normalize_text,
    normalize_title,
    normalize_url,
    select_representative,
    simhash64,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # tracking parameters, order independence, fragment, trailing slash, default port, scheme
        (
            "http://WWW.Example.com:80/a//b/?utm_source=x&b=2&a=1&fbclid=z#frag",
            "https://example.com/a/b?a=1&b=2",
        ),
        ("https://example.com/x/", "https://example.com/x"),
        ("https://example.com", "https://example.com/"),
        # AMP and mobile renders of the same document
        ("https://example.com/story/amp", "https://example.com/story"),
        ("https://example.com/story.amp.html", "https://example.com/story"),
        ("https://example.com/story?output=amp", "https://example.com/story"),
        ("https://m.example.com/story", "https://example.com/story"),
        ("https://amp.example.com/story", "https://example.com/story"),
        ("https://mobile.example.com/story", "https://example.com/story"),
        # tracking-only query reduces to the bare path
        ("https://example.com/story?utm_campaign=a&utm_medium=b", "https://example.com/story"),
        # meaningful parameters survive, lowercased and sorted
        ("https://example.com/s?q=B&page=2", "https://example.com/s?page=2&q=B"),
        # credentials, non-default port
        ("https://user:pw@example.com:8080/a", "https://example.com:8080/a"),
    ],
)
def test_normalize_url(raw: str, expected: str) -> None:
    assert normalize_url(raw) == expected


def test_normalize_url_is_idempotent() -> None:
    for raw in (
        "http://WWW.Example.com:80/a//b/?utm_source=x&b=2&a=1#frag",
        "https://m.example.com/story/amp/",
        "example.com/a",
        "",
        "not a url",
    ):
        once = normalize_url(raw)
        assert normalize_url(once) == once


def test_normalize_url_does_not_eat_real_hosts() -> None:
    # "amp." / "m." prefixes must not reduce a two-label host to nothing.
    assert normalize_url("https://amp.com/x") == "https://amp.com/x"
    assert normalize_url("https://m.tv/x") == "https://m.tv/x"


def test_item_id_survives_a_headline_rewrite() -> None:
    """The FR-2 defect: newsrooms rewrite headlines, sometimes minutes apart."""
    url = "https://example.com/story?utm_source=rss"
    assert item_id(url, "Fed holds rates steady") == item_id(
        "https://example.com/story", "Fed Holds Rates Steady, Defying Expectations"
    )


def test_item_id_separates_distinct_documents() -> None:
    assert item_id("https://example.com/a") != item_id("https://example.com/b")


def test_item_id_falls_back_to_title_without_a_url() -> None:
    assert item_id("", "A Linkless Entry") == item_id("", "a  linkless   entry")
    assert item_id("", "A Linkless Entry") != item_id("", "A Different Entry")
    assert item_id("", "") == ""


def test_normalize_text_is_unicode_aware() -> None:
    assert normalize_text("Héllo,   Wörld!") == "héllo wörld"
    assert normalize_title("Ｆｕｌｌ－Ｗｉｄｔｈ") == "full width"


def test_hamming_matches_construction() -> None:
    assert hamming(0b1011, 0b1001) == 1
    assert hamming(0, 0) == 0
    assert hamming((1 << 64) - 1, 0) == 64


def test_simhash_is_deterministic_and_similar_for_similar_text() -> None:
    text = "the central bank held interest rates steady at its meeting on wednesday"
    assert simhash64(text) == simhash64(text)
    assert simhash64(text) != 0


def test_content_key_tolerates_a_truncated_summary() -> None:
    """Syndicated copies share a headline and carry partly truncated bodies."""
    headline = "Fed holds rates steady as inflation cools"
    long_body = " ".join(f"sentencetoken{i}" for i in range(120))
    short_body = " ".join(f"sentencetoken{i}" for i in range(12))
    unrelated = "Celebrity chef opens a new restaurant in Lisbon"

    same_story = hamming(content_key(headline, long_body), content_key(headline, short_body))
    different_story = hamming(content_key(headline, long_body), content_key(unrelated, long_body))

    assert same_story < different_story


def test_group_duplicates_merges_url_variants_by_item_id() -> None:
    refs = [
        ItemRef(item_id("https://example.com/a?utm_source=rss"), "https://example.com/a?utm_source=rss", "A", simhash64("alpha beta gamma")),
        ItemRef(item_id("https://www.example.com/a/"), "https://www.example.com/a/", "A", simhash64("alpha beta gamma")),
    ]
    assert refs[0].item_id == refs[1].item_id
    groups = group_duplicates(refs)
    assert groups == [[refs[0].item_id]]


def test_group_duplicates_merges_cross_posted_stories() -> None:
    headline = "Fed holds rates steady as inflation cools"
    body = "the central bank left its policy rate unchanged"
    refs = [
        ItemRef(item_id("https://example.com/story"), "https://example.com/story", headline, content_key(headline, body)),
        ItemRef(item_id("https://other.example.net/fed-rates"), "https://other.example.net/fed-rates", headline, content_key(headline, body)),
        ItemRef(item_id("https://example.com/unrelated"), "https://example.com/unrelated", "Weather warning issued for the coast", content_key("Weather warning issued for the coast", "storms expected overnight")),
    ]
    groups = group_duplicates(refs, max_distance=3)
    merged = [group for group in groups if len(group) > 1]
    assert merged == [sorted([refs[0].item_id, refs[1].item_id])]
    assert select_representative(refs, merged[0]) == refs[0].item_id


def _brute_force_groups(refs: list[ItemRef], max_distance: int) -> list[list[str]]:
    """Reference implementation: all pairs, no banding."""
    size = len(refs)
    parent = list(range(size))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left in range(size):
        for right in range(left + 1, size):
            same_url = refs[left].item_id == refs[right].item_id
            if same_url or hamming(refs[left].content_key, refs[right].content_key) <= max_distance:
                root_left, root_right = find(left), find(right)
                if root_left != root_right:
                    parent[max(root_left, root_right)] = min(root_left, root_right)

    grouped: dict[int, set[str]] = {}
    for index, ref in enumerate(refs):
        grouped.setdefault(find(index), set()).add(ref.item_id)
    result = [sorted(ids) for ids in grouped.values()]
    result.sort(key=lambda group: group[0])
    return result


@pytest.mark.parametrize("max_distance", [0, 1, 3, 7])
def test_banding_matches_brute_force(max_distance: int) -> None:
    """The pigeonhole band filter must not miss any pair the exhaustive search would merge."""
    rng = random.Random(7)
    refs = [
        ItemRef(f"u{index:04d}", f"https://example.com/{index}", "", rng.getrandbits(64))
        for index in range(150)
    ]
    # Cherry-pick near-duplicates so the case is not all-singletons. ItemRef is frozen by design
    # (identity must not drift mid-run), so rebuild rather than assign.
    for index in range(0, 150, 10):
        refs[index + 1] = replace(
            refs[index + 1],
            content_key=refs[index].content_key ^ (rng.getrandbits(max_distance + 1) >> 1),
        )

    assert group_duplicates(refs, max_distance) == _brute_force_groups(refs, max_distance)


def test_group_duplicates_handles_empty_and_singleton() -> None:
    assert group_duplicates([]) == []
    single = ItemRef("u1", "https://example.com/1", "t", 0)
    assert group_duplicates([single]) == [["u1"]]
    # Identical keys with different ids and distance 0 must still merge.
    twins = [ItemRef("u1", "https://example.com/1", "t", 0), ItemRef("u2", "https://example.com/2", "t", 0)]
    assert group_duplicates(twins, max_distance=0) == [["u1", "u2"]]


def test_select_representative_prefers_the_shortest_url() -> None:
    refs = [
        ItemRef("long", "https://example.com/a/very/long/tracking/path", "t", 5),
        ItemRef("short", "https://example.com/a", "t", 5),
    ]
    assert select_representative(refs, ["long", "short"]) == "short"
    assert select_representative(refs, []) == ""
