import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gcalendar.calendar_policy import CalendarPolicyError, load_calendar_write_policy
from gcalendar.calendar_tools import (
    _create_event_impl,
    _delete_event_impl,
    _modify_event_impl,
)


def _clear_policy_cache():
    cache_clear = getattr(load_calendar_write_policy, "cache_clear", None)
    if cache_clear:
        cache_clear()


@pytest.fixture(autouse=True)
def _reset_policy_cache():
    _clear_policy_cache()
    yield
    _clear_policy_cache()


class _FakeRequest:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeEventsResource:
    def __init__(self, existing_event=None):
        self.existing_event = existing_event or {
            "id": "evt-123",
            "summary": "Existing",
            "attendees": [],
        }
        self.insert_called = False
        self.update_called = False
        self.delete_called = False
        self.get_called = False

    def insert(self, **kwargs):
        self.insert_called = True
        return _FakeRequest(
            {
                "id": "evt-created",
                "summary": kwargs["body"].get("summary", "Created"),
                "htmlLink": "https://example.com/created",
            }
        )

    def get(self, **kwargs):
        self.get_called = True
        return _FakeRequest(self.existing_event)

    def update(self, **kwargs):
        self.update_called = True
        return _FakeRequest(
            {
                "id": kwargs["eventId"],
                "summary": kwargs["body"].get("summary", "Updated"),
                "htmlLink": "https://example.com/updated",
            }
        )

    def delete(self, **kwargs):
        self.delete_called = True
        return _FakeRequest({})


class _FakeCalendarService:
    def __init__(self, existing_event=None):
        self._events = _FakeEventsResource(existing_event=existing_event)
        self._http = None

    def events(self):
        return self._events


@pytest.mark.asyncio
async def test_create_event_rejects_disallowed_attendee(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "kah411@pitt.edu")
    service = _FakeCalendarService()

    with pytest.raises(CalendarPolicyError, match="disallowed attendee"):
        await _create_event_impl(
            service=service,
            user_google_email="me@example.com",
            summary="Test",
            start_time="2026-03-08T10:00:00Z",
            end_time="2026-03-08T11:00:00Z",
            calendar_id="primary",
            attendees=["other@example.com"],
        )

    assert service._events.insert_called is False


@pytest.mark.asyncio
async def test_create_event_allows_no_attendees_with_empty_attendee_allowlist(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "")
    service = _FakeCalendarService()

    result = await _create_event_impl(
        service=service,
        user_google_email="me@example.com",
        summary="Solo block",
        start_time="2026-03-08T10:00:00Z",
        end_time="2026-03-08T11:00:00Z",
        calendar_id="primary",
        attendees=None,
    )

    assert "Successfully created event" in result
    assert service._events.insert_called is True


@pytest.mark.asyncio
async def test_create_event_rejects_guests_can_invite_others(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "kah411@pitt.edu")
    service = _FakeCalendarService()

    with pytest.raises(CalendarPolicyError, match="guestsCanInviteOthers"):
        await _create_event_impl(
            service=service,
            user_google_email="me@example.com",
            summary="Unsafe",
            start_time="2026-03-08T10:00:00Z",
            end_time="2026-03-08T11:00:00Z",
            calendar_id="primary",
            attendees=["kah411@pitt.edu"],
            guests_can_invite_others=True,
        )

    assert service._events.insert_called is False


@pytest.mark.asyncio
async def test_modify_event_rejects_existing_disallowed_attendee(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "kah411@pitt.edu")
    service = _FakeCalendarService(
        existing_event={
            "id": "evt-123",
            "summary": "Existing",
            "attendees": [{"email": "other@example.com"}],
        }
    )

    with pytest.raises(
        CalendarPolicyError, match="existing event contains disallowed attendee"
    ):
        await _modify_event_impl(
            service=service,
            user_google_email="me@example.com",
            event_id="evt-123",
            calendar_id="primary",
            summary="Updated title",
        )

    assert service._events.get_called is True
    assert service._events.update_called is False


@pytest.mark.asyncio
async def test_delete_event_rejects_existing_disallowed_attendee(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS", "primary")
    monkeypatch.setenv("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS", "kah411@pitt.edu")
    service = _FakeCalendarService(
        existing_event={
            "id": "evt-123",
            "summary": "Existing",
            "attendees": [{"email": "other@example.com"}],
        }
    )

    with pytest.raises(
        CalendarPolicyError, match="existing event contains disallowed attendee"
    ):
        await _delete_event_impl(
            service=service,
            user_google_email="me@example.com",
            event_id="evt-123",
            calendar_id="primary",
        )

    assert service._events.get_called is True
    assert service._events.delete_called is False
