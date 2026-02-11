import httpx

from varaosabotti.models import CategoryStatus
from varaosabotti.scraper import (
    fetch_page,
    find_category,
    parse_categories,
    suggest_categories,
)


# --- parse_categories ---


def test_parse_categories_count(sample_html):
    cats = parse_categories(sample_html)
    assert len(cats) == 5


def test_parse_categories_skips_suosittuja(sample_html):
    cats = parse_categories(sample_html)
    names = [c.title for c in cats]
    assert "Popular Item" not in names


def test_parse_categories_skips_kaikki(sample_html):
    cats = parse_categories(sample_html)
    names = [c.title for c in cats]
    assert "Kaikki" not in names


def test_parse_categories_active_inactive(sample_html):
    cats = parse_categories(sample_html)
    by_title = {c.title: c for c in cats}
    assert by_title["Active Simple"].status == CategoryStatus.ACTIVE
    assert by_title["Inactive Simple"].status == CategoryStatus.INACTIVE


def test_parse_categories_group(sample_html):
    cats = parse_categories(sample_html)
    for c in cats:
        assert c.group == "Test Group"


def test_parse_categories_dropdown_parent(sample_html):
    cats = parse_categories(sample_html)
    by_title = {c.title: c for c in cats}
    assert by_title["Child Active"].parent == "Parent Toggle"
    assert by_title["Child Inactive"].parent == "Parent Toggle"
    assert by_title["Parent Toggle"].parent is None


def test_parse_categories_empty_html():
    assert parse_categories("<html><body></body></html>") == []


# --- find_category ---


def test_find_single_name(sample_categories):
    matches = find_category(sample_categories, "Active Simple")
    assert len(matches) == 1
    assert matches[0].title == "Active Simple"


def test_find_case_insensitive(sample_categories):
    matches = find_category(sample_categories, "active simple")
    assert len(matches) == 1


def test_find_no_match(sample_categories):
    assert find_category(sample_categories, "Nonexistent") == []


def test_find_no_substring_match(sample_categories):
    """Exact matching only — 'Active' should NOT match 'Active Simple'."""
    assert find_category(sample_categories, "Active") == []


def test_find_two_segment_parent_child(sample_categories):
    matches = find_category(sample_categories, "Parent Toggle / Child Active")
    assert len(matches) == 1
    assert matches[0].title == "Child Active"


def test_find_three_segment(sample_categories):
    matches = find_category(sample_categories, "Test Group / Parent Toggle / Child Active")
    assert len(matches) == 1
    assert matches[0].title == "Child Active"


def test_find_two_segment_group_name(sample_categories):
    """Two segments can also be group / name for top-level items."""
    matches = find_category(sample_categories, "Test Group / Active Simple")
    assert len(matches) == 1
    assert matches[0].title == "Active Simple"


# --- suggest_categories ---


def test_suggest_returns_matches(sample_categories):
    suggestions = suggest_categories(sample_categories, "child")
    assert len(suggestions) == 2
    assert all("Child" in s for s in suggestions)


def test_suggest_no_match(sample_categories):
    assert suggest_categories(sample_categories, "zzz") == []


def test_suggest_max_five():
    """Suggestions are capped at 5."""
    from varaosabotti.models import Category, CategoryStatus

    cats = [
        Category(name=f"Item{i}", title=f"Item{i}", href="/", status=CategoryStatus.ACTIVE)
        for i in range(10)
    ]
    suggestions = suggest_categories(cats, "Item")
    assert len(suggestions) == 5


# --- fetch_page ---


def test_fetch_page(httpx_mock):
    httpx_mock.add_response(url="https://example.com", text="<html>ok</html>")
    client = httpx.Client()
    result = fetch_page("https://example.com", client)
    assert result == "<html>ok</html>"
    client.close()
