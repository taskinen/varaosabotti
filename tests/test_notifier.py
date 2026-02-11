import logging

import httpx

from varaosabotti.models import Category, CategoryStatus
from varaosabotti.notifier import category_label, log_alert, notify, send_pushover


def _make_cat(*, parent=None, group=None):
    return Category(
        name="Test",
        title="Test Cat",
        href="/test",
        status=CategoryStatus.ACTIVE,
        group=group,
        parent=parent,
    )


# --- category_label ---


def test_label_simple():
    assert category_label(_make_cat()) == "Test Cat"


def test_label_with_group():
    assert category_label(_make_cat(group="G")) == "Test Cat  (G)"


def test_label_with_parent():
    assert category_label(_make_cat(parent="P")) == "P / Test Cat"


def test_label_with_parent_and_group():
    assert category_label(_make_cat(parent="P", group="G")) == "P / Test Cat  (G)"


# --- log_alert ---


def test_log_alert(caplog):
    cat = _make_cat(group="G")
    with caplog.at_level(logging.WARNING):
        log_alert(cat, "https://example.com")
    assert "ALERT" in caplog.text
    assert "Test Cat" in caplog.text


# --- send_pushover ---


def test_send_pushover_success(httpx_mock):
    httpx_mock.add_response(
        url="https://api.pushover.net/1/messages.json",
        json={"status": 1},
    )
    cat = _make_cat()
    client = httpx.Client()
    send_pushover(cat, "https://example.com", "tok", "usr", client)
    client.close()

    request = httpx_mock.get_request()
    assert b"tok" in request.content
    assert b"usr" in request.content


def test_send_pushover_http_error(httpx_mock, caplog):
    httpx_mock.add_response(
        url="https://api.pushover.net/1/messages.json",
        status_code=400,
        json={"errors": ["invalid token"]},
    )
    cat = _make_cat()
    client = httpx.Client()
    with caplog.at_level(logging.ERROR):
        send_pushover(cat, "https://example.com", "tok", "usr", client)
    client.close()
    assert "invalid token" in caplog.text


# --- notify ---


def test_notify_without_pushover(caplog):
    cat = _make_cat()
    client = httpx.Client()
    with caplog.at_level(logging.WARNING):
        notify(cat, "https://example.com", None, None, client)
    client.close()
    assert "ALERT" in caplog.text


def test_notify_with_pushover(httpx_mock, caplog):
    httpx_mock.add_response(
        url="https://api.pushover.net/1/messages.json",
        json={"status": 1},
    )
    cat = _make_cat()
    client = httpx.Client()
    with caplog.at_level(logging.WARNING):
        notify(cat, "https://example.com", "tok", "usr", client)
    client.close()
    assert "ALERT" in caplog.text
    assert httpx_mock.get_request() is not None
