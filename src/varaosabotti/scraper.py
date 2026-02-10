import logging

import httpx
from bs4 import BeautifulSoup, Tag

from varaosabotti.models import Category, CategoryStatus

logger = logging.getLogger(__name__)

USER_AGENT = "varaosabotti/0.1.0"


def fetch_page(url: str, client: httpx.Client) -> str:
    response = client.get(url)
    response.raise_for_status()
    return response.text


def parse_categories(html: str) -> list[Category]:
    soup = BeautifulSoup(html, "lxml")
    categories: list[Category] = []

    # Find all ngbdropdown containers that hold category links
    containers = soup.select("div[ngbdropdown].col-lg-4")

    for container in containers:
        group = _find_group_header(container)

        # Skip the "Suosittuja osia" (popular parts) section to avoid duplicates
        if group and "suosittuja" in group.lower():
            continue

        # Simple category link (not a dropdown)
        simple_link = container.select_one(
            'a[queryparamshandling="preserve"]:not([ngbdropdownitem])'
        )
        if simple_link and isinstance(simple_link, Tag) and not simple_link.has_attr("ngbdropdowntoggle"):
            cat = _parse_link(simple_link, group)
            if cat:
                categories.append(cat)
            continue

        # Dropdown toggle parent
        toggle = container.select_one("a[ngbdropdowntoggle]")
        if toggle and isinstance(toggle, Tag):
            # Add the parent toggle first
            parent_cat = _parse_link(toggle, group)
            if parent_cat:
                categories.append(parent_cat)
                parent_name = parent_cat.title
            else:
                parent_name = None

            # Then add dropdown sub-items (skip "Kaikki" which is just "All")
            items = container.select("a[ngbdropdownitem]")
            for item in items:
                if isinstance(item, Tag):
                    title = item.get("title", "")
                    if title == "Kaikki":
                        continue
                    cat = _parse_link(item, group, parent=parent_name)
                    if cat:
                        categories.append(cat)

    logger.debug(
        "Parsed %d categories (%d active, %d inactive)",
        len(categories),
        sum(1 for c in categories if c.status == CategoryStatus.ACTIVE),
        sum(1 for c in categories if c.status == CategoryStatus.INACTIVE),
    )
    return categories


def find_category(categories: list[Category], name: str) -> list[Category]:
    parts = [p.strip() for p in name.split("/")]

    if len(parts) == 3:
        # Group / Parent / Child
        group_s, parent_s, child_s = (p.lower() for p in parts)
        return [
            c
            for c in categories
            if c.group
            and c.parent
            and c.group.lower() == group_s
            and c.parent.lower() == parent_s
            and _name_matches(c, child_s)
        ]

    if len(parts) == 2:
        first, second = parts[0].lower(), parts[1].lower()

        # Try parent / child first
        parent_child = [
            c
            for c in categories
            if c.parent
            and c.parent.lower() == first
            and _name_matches(c, second)
        ]
        if parent_child:
            return parent_child

        # Try group / name
        return [
            c
            for c in categories
            if c.group
            and c.group.lower() == first
            and _name_matches(c, second)
        ]

    # Single name — exact match on title or name
    name_lower = name.lower()
    return [c for c in categories if _name_matches(c, name_lower)]


def suggest_categories(categories: list[Category], name: str) -> list[str]:
    """Return up to 5 category titles containing the search term as a substring."""
    name_lower = name.lower()
    suggestions: list[str] = []
    for c in categories:
        if name_lower in c.title.lower() or name_lower in c.name.lower():
            label = f"{c.parent} / {c.title}" if c.parent else c.title
            if c.group:
                label += f"  ({c.group})"
            if label not in suggestions:
                suggestions.append(label)
            if len(suggestions) >= 5:
                break
    return suggestions


def _name_matches(cat: Category, search: str) -> bool:
    return cat.title.lower() == search or cat.name.lower() == search


def _get_status(tag: Tag) -> CategoryStatus:
    classes = tag.get("class", [])
    if "disabled-link" in classes:
        return CategoryStatus.INACTIVE
    return CategoryStatus.ACTIVE


def _parse_link(
    tag: Tag, group: str | None, parent: str | None = None
) -> Category | None:
    span = tag.select_one("span")
    name = span.get_text(strip=True) if span else ""
    title = str(tag.get("title", name))
    href = str(tag.get("href", ""))

    if not name:
        return None

    return Category(
        name=name,
        title=title,
        href=href,
        status=_get_status(tag),
        group=group,
        parent=parent,
    )


def _find_group_header(container: Tag) -> str | None:
    # Walk up to the parent div.col-12 and find its h4
    col12 = container.find_parent("div", class_="col-12")
    if col12 and isinstance(col12, Tag):
        h4 = col12.find("h4")
        if h4 and isinstance(h4, Tag):
            return h4.get_text(strip=True)
    return None
