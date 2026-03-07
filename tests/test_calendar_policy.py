import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gcalendar.calendar_policy import (
    CalendarPolicyError,
    extract_attendee_emails,
    extract_event_attendee_emails,
    load_calendar_write_policy,
)


@pytest.fixture(autouse=True)
def _reset_policy_cache():
    load_calendar_write_policy.cache_clear()
    yield
    load_calendar_write_policy.cache_clear()


def test_policy_denies_writes_when_calendar_allowlist_missing(monkeypatch):
    monkeypatch.delenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", raising=False)
    monkeypatch.delenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", raising=False)

    policy = load_calendar_write_policy()

    with pytest.raises(CalendarPolicyError, match="calendar writes are disabled"):
        policy.validate_create(
            calendar_id="primary",
            attendees=[],
            guests_can_invite_others=False,
        )


def test_policy_normalizes_emails_and_calendar_ids(monkeypatch):
    monkeypatch.setenv(
        "WORKSPACE_MCP_ALLOWED_CALENDAR_IDS",
        "primary, work@example.com ",
    )
    monkeypatch.setenv(
        "WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS",
        " Kah411@PITT.EDU ",
    )

    policy = load_calendar_write_policy()

    assert policy.allowed_calendar_ids == {"primary", "work@example.com"}
    assert policy.allowed_attendee_emails == {"kah411@pitt.edu"}


def test_policy_allows_no_attendees_when_attendee_allowlist_empty(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "")

    policy = load_calendar_write_policy()

    policy.validate_create(
        calendar_id="primary",
        attendees=[],
        guests_can_invite_others=False,
    )


def test_extract_attendee_emails_ignores_entries_without_email():
    attendees = [
        "One@example.com",
        {"email": "Two@example.com", "responseStatus": "accepted"},
        {"displayName": "Symbolic only"},
        {"email": " one@example.com "},
    ]

    assert extract_attendee_emails(attendees) == [
        "one@example.com",
        "two@example.com",
    ]


def test_extract_event_attendee_emails_ignores_non_email_entries():
    event = {
        "attendees": [
            {"email": "kah411@pitt.edu"},
            {"self": True},
            {"organizer": True},
        ]
    }

    assert extract_event_attendee_emails(event) == ["kah411@pitt.edu"]


def test_policy_rejects_guests_can_invite_others(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "kah411@pitt.edu")

    policy = load_calendar_write_policy()

    with pytest.raises(CalendarPolicyError, match="guestsCanInviteOthers"):
        policy.validate_create(
            calendar_id="primary",
            attendees=["kah411@pitt.edu"],
            guests_can_invite_others=True,
        )


def test_policy_rejects_existing_event_with_disallowed_attendee(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "kah411@pitt.edu")

    policy = load_calendar_write_policy()

    with pytest.raises(
        CalendarPolicyError, match="existing event contains disallowed attendee"
    ):
        policy.validate_existing_event(
            calendar_id="primary",
            event={"attendees": [{"email": "other@example.com"}]},
        )
