import argparse
import logging
import os
import sys
import time

import httpx

from varaosabotti.models import CategoryStatus
from varaosabotti.notifier import category_label, notify, send_pushover
from varaosabotti.scraper import (
    fetch_page,
    find_category,
    parse_categories,
    suggest_categories,
)

logger = logging.getLogger("varaosabotti")


def configure_logging(*, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Suppress noisy httpx request logging unless in verbose mode
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="varaosabotti",
        description="Monitor varaosahaku.fi for car parts availability.",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("VARAOSABOTTI_URL"),
        help="Varaosahaku.fi category page URL (env: VARAOSABOTTI_URL)",
    )
    parser.add_argument(
        "--category",
        default=os.environ.get("VARAOSABOTTI_CATEGORY"),
        help="Category name to monitor (env: VARAOSABOTTI_CATEGORY)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("VARAOSABOTTI_INTERVAL", "300")),
        help="Polling interval in seconds (default: 300, env: VARAOSABOTTI_INTERVAL)",
    )
    parser.add_argument(
        "--pushover-token",
        default=os.environ.get("PUSHOVER_TOKEN"),
        help="Pushover application API token (env: PUSHOVER_TOKEN)",
    )
    parser.add_argument(
        "--pushover-user",
        default=os.environ.get("PUSHOVER_USER"),
        help="Pushover user key (env: PUSHOVER_USER)",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="Fetch page and print all categories with their status, then exit.",
    )
    parser.add_argument(
        "--test-notification",
        action="store_true",
        help="Send a test Pushover notification and exit.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def _create_client() -> httpx.Client:
    return httpx.Client(
        timeout=30.0,
        headers={"User-Agent": "varaosabotti/0.1.0", "Accept-Language": "fi"},
        follow_redirects=True,
    )


def list_categories(url: str) -> None:
    client = _create_client()
    try:
        html = fetch_page(url, client)
        categories = parse_categories(html)

        if not categories:
            print("No categories found. Check the URL.")
            return

        current_group = None
        for cat in categories:
            if cat.group != current_group:
                current_group = cat.group
                print(f"\n  {current_group or 'Uncategorized'}")
                print(f"  {'─' * 50}")

            status_marker = "+" if cat.status == CategoryStatus.ACTIVE else "-"
            if cat.parent:
                label = f"{cat.parent} / {cat.title}"
                print(f"        [{status_marker}] {label}")
            else:
                print(f"    [{status_marker}] {cat.title}")

        active = sum(1 for c in categories if c.status == CategoryStatus.ACTIVE)
        total = len(categories)
        print(f"\n  Total: {total} categories ({active} active, {total - active} inactive)")
    finally:
        client.close()


def run_monitor(args: argparse.Namespace) -> None:
    client = _create_client()
    previously_active = False

    # Validate category exists before starting the polling loop
    try:
        html = fetch_page(args.url, client)
        categories = parse_categories(html)
        matches = find_category(categories, args.category)

        if not matches:
            logger.error("Category '%s' not found on page.", args.category)
            suggestions = suggest_categories(categories, args.category)
            if suggestions:
                logger.error("Did you mean one of these?")
                for s in suggestions:
                    logger.error("  - %s", s)
            logger.error("Use --list-categories to see all available names.")
            sys.exit(1)

        logger.info(
            "Monitoring '%s' (%d match(es)) on %s (interval: %ds)",
            args.category,
            len(matches),
            args.url,
            args.interval,
        )
        for m in matches:
            logger.info("  Matched: %s", category_label(m))
    except httpx.HTTPError:
        logger.warning("Could not validate category (network error). Starting monitor anyway.")
        html = None

    if args.pushover_token and args.pushover_user:
        logger.info("Pushover notifications enabled.")

    try:
        first_iteration = True
        while True:
            try:
                # Reuse the HTML from validation on the first iteration
                if first_iteration and html:
                    first_iteration = False
                else:
                    html = fetch_page(args.url, client)
                    categories = parse_categories(html)

                matches = find_category(categories, args.category)

                if not matches:
                    logger.warning(
                        "Category '%s' no longer found on page.",
                        args.category,
                    )
                elif any(m.status == CategoryStatus.ACTIVE for m in matches):
                    if not previously_active:
                        for m in matches:
                            if m.status == CategoryStatus.ACTIVE:
                                notify(m, args.url, args.pushover_token, args.pushover_user, client)
                        previously_active = True
                    else:
                        logger.debug("Category '%s' is still active (already notified).", args.category)
                else:
                    for m in matches:
                        logger.info("Still inactive: %s", category_label(m))
                    previously_active = False

            except httpx.HTTPStatusError as exc:
                logger.warning("HTTP error %d fetching page. Will retry.", exc.response.status_code)
            except httpx.HTTPError:
                logger.warning("Network error fetching page. Will retry.", exc_info=True)

            if args.once:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Monitor stopped.")
    finally:
        client.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(verbose=args.verbose)

    if args.test_notification:
        if not args.pushover_token or not args.pushover_user:
            parser.error("--pushover-token and --pushover-user are required for --test-notification")
        from varaosabotti.models import Category, CategoryStatus

        test_cat = Category(
            name="Test",
            title="Test Notification",
            href="",
            status=CategoryStatus.ACTIVE,
            group="varaosabotti",
        )
        client = _create_client()
        try:
            send_pushover(test_cat, "https://www.varaosahaku.fi", args.pushover_token, args.pushover_user, client)
        finally:
            client.close()
        sys.exit(0)

    if not args.url:
        parser.error("--url is required (or set VARAOSABOTTI_URL)")

    if args.list_categories:
        list_categories(args.url)
        sys.exit(0)

    if not args.category:
        parser.error("--category is required (or set VARAOSABOTTI_CATEGORY)")

    run_monitor(args)
