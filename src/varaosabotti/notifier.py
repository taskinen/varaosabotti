import logging

import httpx

from varaosabotti.models import Category

logger = logging.getLogger(__name__)

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


def category_label(cat: Category) -> str:
    label = f"{cat.parent} / {cat.title}" if cat.parent else cat.title
    if cat.group:
        label += f"  ({cat.group})"
    return label


def log_alert(category: Category, url: str) -> None:
    logger.warning(
        "ALERT: '%s' is now ACTIVE — parts are available! URL: %s",
        category_label(category),
        url,
    )


def send_pushover(
    category: Category,
    url: str,
    api_token: str,
    user_key: str,
    client: httpx.Client,
) -> None:
    label = category_label(category)
    payload = {
        "token": api_token,
        "user": user_key,
        "title": f"Varaosabotti: {label}",
        "message": f"Parts are now available for '{label}'!",
        "url": url,
        "url_title": "View on varaosahaku.fi",
        "priority": 1,
        "sound": "bugle",
    }
    try:
        response = client.post(PUSHOVER_API_URL, data=payload)
        response.raise_for_status()
        logger.info("Pushover notification sent for '%s'.", label)
    except httpx.HTTPStatusError as exc:
        try:
            errors = exc.response.json().get("errors", [])
            detail = "; ".join(errors) if errors else f"HTTP {exc.response.status_code}"
        except Exception:
            detail = f"HTTP {exc.response.status_code}"
        logger.error("Pushover error: %s", detail)
    except httpx.HTTPError:
        logger.error("Failed to send Pushover notification (network error).")


def notify(
    category: Category,
    url: str,
    pushover_token: str | None,
    pushover_user: str | None,
    client: httpx.Client,
) -> None:
    log_alert(category, url)
    if pushover_token and pushover_user:
        send_pushover(category, url, pushover_token, pushover_user, client)
