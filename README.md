# varaosabotti

[![CI](https://github.com/taskinen/varaosabotti/actions/workflows/ci.yml/badge.svg)](https://github.com/taskinen/varaosabotti/actions/workflows/ci.yml)

A CLI tool that monitors [varaosahaku.fi](https://www.varaosahaku.fi) (a Finnish car parts marketplace) for parts availability. Give it a category page URL and a category name, and it will poll the page and alert you when parts become available.

Alerts are logged to the console and optionally pushed to your phone via [Pushover](https://pushover.net).

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
git clone https://github.com/taskinen/varaosabotti.git
cd varaosabotti
uv sync
```

## Quick start

**1. Find your category page URL** on varaosahaku.fi. Navigate to a car model and select a part group. Copy the URL from the browser — it will look something like:

```
https://www.varaosahaku.fi/fi-fi/pb/Hae/Autonosat/s19/Polestar/2/Sisusta
```

**2. List available categories** to see what you can monitor:

```bash
varaosabotti --url 'https://www.varaosahaku.fi/fi-fi/pb/Hae/Autonosat/s19/Polestar/2/Sisusta' --list-categories
```

This prints all categories grouped by section, with `[+]` for available and `[-]` for unavailable parts.

**3. Start monitoring** a category:

```bash
varaosabotti --url '...' --category 'Kattoverhoilu' --interval 60
```

The tool will poll the page every 60 seconds and log an alert when the category becomes active.

## Usage

```
varaosabotti [OPTIONS]
```

| Option | Default | Env var | Description |
|---|---|---|---|
| `--url URL` | | `VARAOSABOTTI_URL` | Category page URL to monitor |
| `--category NAME` | | `VARAOSABOTTI_CATEGORY` | Category name to watch |
| `--interval SECS` | 300 | `VARAOSABOTTI_INTERVAL` | Poll interval in seconds |
| `--pushover-token TOKEN` | | `PUSHOVER_TOKEN` | Pushover API token |
| `--pushover-user KEY` | | `PUSHOVER_USER` | Pushover user key |
| `--list-categories` | | | Print all categories and exit |
| `--test-notification` | | | Send a test push notification and exit |
| `--once` | | | Run a single check and exit |
| `--verbose` | | | Enable debug logging |

All options that accept env vars can be set either way. Command-line flags take precedence.

## Category names

Categories are matched **exactly** (case-insensitive). Some categories share the same name across different sections. Use `/`-separated paths to disambiguate:

```bash
# Simple name
varaosabotti --url '...' --category 'Kattoverhoilu'

# Parent / child
varaosabotti --url '...' --category 'Oviverhoilu / Vasen'

# Group / parent / child (fully qualified)
varaosabotti --url '...' --category 'Sisusta Ovet / Oviverhoilu / Vasen'
```

If a category is not found, the tool suggests similar names and exits.

## Pushover notifications

To receive push notifications on your phone:

1. Create an account at [pushover.net](https://pushover.net) — your **user key** is shown on the dashboard after login
2. [Create a new application](https://pushover.net/apps/build) (e.g. "varaosabotti") — this gives you an **application API token**
3. Pass both credentials:

```bash
varaosabotti --url '...' --category 'Kattoverhoilu' \
  --pushover-token YOUR_APP_TOKEN \
  --pushover-user YOUR_USER_KEY
```

Test your setup without monitoring:

```bash
varaosabotti --pushover-token YOUR_APP_TOKEN --pushover-user YOUR_USER_KEY --test-notification
```

## Running with environment variables

For long-running use, environment variables avoid repeating arguments:

```bash
export VARAOSABOTTI_URL='https://www.varaosahaku.fi/fi-fi/pb/Hae/Autonosat/s19/Polestar/2/Sisusta'
export VARAOSABOTTI_CATEGORY='Kattoverhoilu'
export VARAOSABOTTI_INTERVAL=60
export PUSHOVER_TOKEN=your_token
export PUSHOVER_USER=your_key

varaosabotti
```

## How it works

1. Fetches the category page via HTTP GET (the site uses Angular SSR, so server-rendered HTML is returned directly — no headless browser needed)
2. Parses the HTML to extract categories and their active/inactive status
3. Checks if the monitored category has transitioned from inactive to active
4. Sends an alert on the transition (only once per transition, not every poll cycle)
5. Sleeps for the configured interval and repeats

The tool is resilient to transient errors: network failures and HTTP errors are logged and polling continues.

## Development

```bash
uv sync                    # Install dependencies
uv run pytest              # Run tests
uv run ruff check .        # Lint
```
