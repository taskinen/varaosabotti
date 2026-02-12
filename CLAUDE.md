# CLAUDE.md — varaosabotti

> **IMPORTANT**: Keep this file updated whenever you modify the architecture, add modules, change the HTML parsing strategy, or alter CLI arguments. This file is the primary reference for future refactoring sessions.

## What this project does

varaosabotti monitors varaosahaku.fi (a Finnish car parts marketplace) for parts availability. The user provides a category page URL and a category name to watch. The tool polls the page at a configurable interval and alerts (via log + optional Pushover notification) when a monitored category transitions from inactive to active.

## Project setup

- **Package manager**: `uv` (dependencies, virtualenv, running)
- **Build backend**: `uv_build` (configured in `pyproject.toml`)
- **Python**: >=3.13
- **Layout**: `src/varaosabotti/` package
- **Entry point**: `varaosabotti.cli:main` (registered as `[project.scripts]`)

```bash
uv sync                    # Install dependencies
uv run varaosabotti --help # Run the tool
uv run pytest              # Run tests
uv run ruff check .        # Lint
```

## Architecture

```
src/varaosabotti/
    __init__.py         # Empty
    __main__.py         # Entry: calls cli.main()
    models.py           # Data classes: Category, CategoryStatus
    scraper.py          # HTTP fetching + HTML parsing
    notifier.py         # Log alerts + Pushover notifications
    cli.py              # Arg parsing, main loop, list-categories, test-notification
tests/
    conftest.py         # Shared fixtures (sample HTML, sample categories)
    test_models.py      # Model tests
    test_scraper.py     # Parser + matching tests
    test_notifier.py    # Notification tests
```

### Module responsibilities

**`models.py`** — Foundational types, no dependencies on other modules.
- `CategoryStatus` enum: `ACTIVE` / `INACTIVE`
- `Category` frozen dataclass: `name`, `title`, `href`, `status`, `group`, `parent`
  - `group`: the `<h4>` section header (e.g., "Sisusta Ovet")
  - `parent`: the dropdown toggle name for sub-items (e.g., "Oviverhoilu" for its "Vasen"/"Oikea" children). `None` for top-level categories.

**`scraper.py`** — Core parsing logic. Depends on `models`.
- `fetch_page(url, client)` — HTTP GET, returns HTML string
- `parse_categories(html)` — BeautifulSoup + lxml parser, returns `list[Category]`
- `find_category(categories, name)` — Exact case-insensitive matching with `/`-separated path support
- `suggest_categories(categories, name)` — Substring suggestions for "did you mean?" on no match

**`notifier.py`** — Alert dispatch. Depends on `models`.
- `category_label(cat)` — Builds human-readable display label (e.g., `"Oviverhoilu / Vasen  (Sisusta Ovet)"`)
- `log_alert(category, url)` — Logs at WARNING level
- `send_pushover(category, url, token, user, client)` — POST to Pushover API with error parsing
- `notify(category, url, token, user, client)` — Orchestrator: always logs, optionally pushes

**`cli.py`** — User-facing CLI. Depends on all modules.
- `build_parser()` — argparse with env var fallbacks
- `list_categories(url)` — Fetch + print all categories with status
- `run_monitor(args)` — Main polling loop with transition detection
- `main()` — Entry point handling `--test-notification`, `--list-categories`, and monitoring

## Varaosahaku.fi HTML parsing strategy

The site uses **Angular SSR** — a plain HTTP GET returns fully rendered HTML (no headless browser needed).

### Page structure

Categories are organized under `<h4>` group headers inside `<div class="col-12">` sections. Each category is in a `<div ngbdropdown class="col-lg-4 col-sm-12 my-1">` container.

Two types of categories:

1. **Simple category** — a single `<a>` link with `queryparamshandling="preserve"` and class `my-2`
2. **Dropdown category** — an `<a ngbdropdowntoggle>` parent with `<a ngbdropdownitem>` children in a `<div ngbdropdownmenu>`

### Active vs inactive detection

The **`disabled-link` CSS class** is the primary discriminator:

| State | CSS classes | `rel` | `tabindex` | `disabled` attr |
|---|---|---|---|---|
| Active | `my-2` | `follow` | `0` | absent |
| Inactive | `my-2 disabled-link text-danger` | `nofollow` | `-1` | `true` |

We only check for `disabled-link` in the class list — it's the most reliable single indicator.

### Parser selectors

```python
# All category containers
soup.select("div[ngbdropdown].col-lg-4")

# Simple link (not a dropdown item, not a toggle)
container.select_one('a[queryparamshandling="preserve"]:not([ngbdropdownitem])')

# Dropdown toggle parent
container.select_one("a[ngbdropdowntoggle]")

# Dropdown sub-items
container.select("a[ngbdropdownitem]")

# Group header: walk up to parent div.col-12, find its <h4>
container.find_parent("div", class_="col-12").find("h4")
```

### Skipped sections

- **"Suosittuja osia"** (Popular parts) — duplicates of categories in the main listing, identified by group header containing "suosittuja"
- **"Kaikki"** dropdown items — means "All", just an aggregate link

## Category matching (`find_category`)

Matching is **exact, case-insensitive** (no substring matching to avoid silent false positives). The `/` character is the path separator.

| Input format | Matching strategy |
|---|---|
| `"Kattoverhoilu"` | Exact match on `title` or `name` |
| `"Oviverhoilu / Vasen"` | 2-segment: try parent/child first, then group/name |
| `"Sisusta Ovet / Oviverhoilu / Vasen"` | 3-segment: group/parent/child |

When no match is found, `suggest_categories` returns up to 5 titles containing the search term as a substring — used for "did you mean?" hints only, never for silent matching.

## CLI arguments

| Arg | Required | Default | Env var | Description |
|---|---|---|---|---|
| `--url` | Yes* | — | `VARAOSABOTTI_URL` | Page URL to monitor |
| `--category` | Yes* | — | `VARAOSABOTTI_CATEGORY` | Category name to watch |
| `--interval` | No | 300 | `VARAOSABOTTI_INTERVAL` | Poll interval (seconds) |
| `--pushover-token` | No | — | `PUSHOVER_TOKEN` | Pushover application API token |
| `--pushover-user` | No | — | `PUSHOVER_USER` | Pushover user key |
| `--list-categories` | No | — | — | Print categories and exit |
| `--test-notification` | No | — | — | Send test Pushover push and exit |
| `--once` | No | — | — | Single check, then exit |
| `--verbose` | No | — | — | DEBUG logging |

*Not required for `--test-notification`.

## Key design decisions

1. **No headless browser** — Angular SSR returns full HTML server-side.
2. **`disabled-link` class as discriminator** — most reliable single indicator for inactive categories across all link types.
3. **Exact matching only** — substring matching was removed because it caused silent false positives (e.g., "foo" matching "Mikrofooni"). Substring is used only for suggestions.
4. **Transition detection** — `previously_active` flag ensures notifications fire only on inactive-to-active transitions, not repeatedly every poll cycle.
5. **Startup validation** — category is validated against the page before the polling loop starts. Invalid categories cause immediate exit with suggestions.
6. **`httpx` over `requests`** — modern, clean timeout handling, connection pooling via passed-in `Client`.
7. **`argparse` over `click`** — stdlib is sufficient for this small CLI surface; env var fallbacks via `os.environ.get()` defaults.

## Error handling

- **Network errors**: logged as WARNING, polling continues
- **HTTP errors**: logged as WARNING with status code, polling continues
- **Pushover errors**: response JSON `errors` array is parsed and shown; never crashes the monitor
- **Category not found at startup**: exit with suggestions
- **Category disappears mid-run**: logged as WARNING, polling continues

## Testing the application

```bash
# List all categories
uv run varaosabotti --url 'https://www.varaosahaku.fi/fi-fi/pb/Hae/Autonosat/s19/Polestar/2/Sisusta' --list-categories

# Single check on active category (should alert)
uv run varaosabotti --url '...' --category 'Kattoverhoilu' --once

# Single check on inactive category
uv run varaosabotti --url '...' --category 'Hattuhylly' --once

# Disambiguated sub-item
uv run varaosabotti --url '...' --category 'Oviverhoilu / Vasen' --once

# Full 3-level path
uv run varaosabotti --url '...' --category 'Sisusta Ovet / Oviverhoilu / Vasen' --once

# Non-existent category (should error with suggestions)
uv run varaosabotti --url '...' --category 'foo' --once

# Test Pushover notification
uv run varaosabotti --pushover-token TOKEN --pushover-user KEY --test-notification

# Continuous monitoring
uv run varaosabotti --url '...' --category 'Hattuhylly' --interval 60 --verbose
```

## Automated tests

```bash
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
```

Tests live in `tests/` and cover the core logic (no CLI integration tests):

| File | Covers |
|---|---|
| `test_models.py` | `Category` frozen dataclass, `CategoryStatus` enum |
| `test_scraper.py` | `parse_categories` (HTML→Category list), `find_category` (all path formats), `suggest_categories`, `fetch_page` |
| `test_notifier.py` | `category_label` (all label variants), `log_alert`, `send_pushover` (success + error), `notify` (with/without Pushover) |

**Fixtures** (`conftest.py`):
- `sample_html` — minimal HTML mimicking varaosahaku.fi structure (simple links, dropdown with children, active/inactive states, "Suosittuja osia" section to skip, "Kaikki" item to skip)
- `sample_categories` — pre-built `Category` list matching the HTML fixture

HTTP mocking uses `pytest-httpx` (provides `httpx_mock` fixture automatically).

## CI

GitHub Actions workflow in `.github/workflows/ci.yml`. Runs on pushes to `main` and on pull requests targeting `main`.

Three parallel jobs:
- **lint** — `uv run ruff check .`
- **test** — `uv run pytest`
- **docker** — copies `docker-compose.yml.example` to `docker-compose.yml`, builds the Docker image, runs a smoke test (`--help`), starts the service with `docker compose up`, and waits for the healthcheck to pass

Uses `astral-sh/setup-uv@v6` for uv installation and dependency caching (lint/test jobs). Python version comes from `.python-version`.

## Docker

`Dockerfile` uses a multi-stage build: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim` for building, `python:3.13-slim-bookworm` for runtime. Runs as non-root `appuser`. Uses Python 3.13 (not 3.14) because 3.14 Docker images have limited availability and the project requires `>=3.13`. Includes a `HEALTHCHECK` that verifies the Python runtime and package are intact (`import varaosabotti`).

`docker-compose.yml.example` is an example Compose file tracked in Git. Copy it to `docker-compose.yml` (which is gitignored) and fill in your own configuration:

```bash
cp docker-compose.yml.example docker-compose.yml
# Edit docker-compose.yml with your URL, category, and optionally Pushover tokens
```

The service runs as a long-running monitor with `restart: unless-stopped`. All configuration is via environment variables.

```bash
docker compose up -d              # Start monitoring in background
docker compose logs -f            # Follow logs
docker compose down               # Stop

# One-off commands
docker compose run --rm varaosabotti --list-categories
docker compose run --rm varaosabotti --once
```

Files: `Dockerfile`, `docker-compose.yml.example`, `.dockerignore`

## Dependencies

**Runtime**: `httpx`, `beautifulsoup4`, `lxml`
**Dev**: `pytest`, `pytest-httpx`, `ruff`
