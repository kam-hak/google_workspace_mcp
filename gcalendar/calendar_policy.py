from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union


class CalendarPolicyError(ValueError):
    """Raised when a calendar mutation violates local policy."""


def _split_env_list(name: str) -> list[str]:
    raw_value = os.getenv(name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def extract_attendee_emails(
    attendees: Optional[Union[List[str], List[Dict[str, Any]]]],
) -> list[str]:
    """
    Extract normalized attendee emails from request payloads.

    Non-string entries and dicts without an ``email`` key are ignored.
    """
    if not attendees:
        return []

    emails: set[str] = set()
    for attendee in attendees:
        if isinstance(attendee, str):
            candidate = attendee.strip()
        elif isinstance(attendee, dict):
            raw_email = attendee.get("email")
            candidate = raw_email.strip() if isinstance(raw_email, str) else ""
        else:
            candidate = ""

        if candidate:
            emails.add(_normalize_email(candidate))

    return sorted(emails)


def extract_event_attendee_emails(event: Optional[Dict[str, Any]]) -> list[str]:
    """Extract normalized attendee emails from an existing Google Calendar event."""
    if not event:
        return []

    attendees = event.get("attendees")
    if not isinstance(attendees, list):
        return []

    return extract_attendee_emails(attendees)


@dataclass(frozen=True)
class CalendarWritePolicy:
    allowed_calendar_ids: set[str]
    allowed_attendee_emails: set[str]

    def validate_target_calendar(self, calendar_id: str) -> None:
        if not self.allowed_calendar_ids:
            raise CalendarPolicyError(
                "calendar writes are disabled because WORKSPACE_MCP_ALLOWED_CALENDAR_IDS is not set"
            )

        if calendar_id not in self.allowed_calendar_ids:
            raise CalendarPolicyError(
                f"calendar '{calendar_id}' is not allowlisted in WORKSPACE_MCP_ALLOWED_CALENDAR_IDS"
            )

    def validate_guests_can_invite_others(
        self, guests_can_invite_others: Optional[bool]
    ) -> None:
        if guests_can_invite_others is True:
            raise CalendarPolicyError(
                "guestsCanInviteOthers must be false for calendar writes"
            )

    def validate_attendee_emails(
        self, attendee_emails: list[str], context: str = "requested attendees"
    ) -> None:
        disallowed = sorted(
            email
            for email in attendee_emails
            if email not in self.allowed_attendee_emails
        )
        if disallowed:
            raise CalendarPolicyError(
                f"{context} contains disallowed attendee emails: {', '.join(disallowed)}"
            )

    def validate_create(
        self,
        calendar_id: str,
        attendees: Optional[Union[List[str], List[Dict[str, Any]]]],
        guests_can_invite_others: Optional[bool],
    ) -> None:
        self.validate_target_calendar(calendar_id)
        self.validate_guests_can_invite_others(guests_can_invite_others)
        self.validate_attendee_emails(extract_attendee_emails(attendees))

    def validate_requested_update(
        self,
        calendar_id: str,
        attendees: Optional[Union[List[str], List[Dict[str, Any]]]],
        guests_can_invite_others: Optional[bool],
    ) -> None:
        self.validate_target_calendar(calendar_id)
        self.validate_guests_can_invite_others(guests_can_invite_others)
        self.validate_attendee_emails(extract_attendee_emails(attendees))

    def validate_existing_event(self, calendar_id: str, event: Dict[str, Any]) -> None:
        self.validate_target_calendar(calendar_id)
        self.validate_attendee_emails(
            extract_event_attendee_emails(event),
            context="existing event",
        )

    def validate_delete(self, calendar_id: str, event: Dict[str, Any]) -> None:
        self.validate_existing_event(calendar_id, event)


@lru_cache(maxsize=1)
def load_calendar_write_policy() -> CalendarWritePolicy:
    return CalendarWritePolicy(
        allowed_calendar_ids=set(_split_env_list("WORKSPACE_MCP_ALLOWED_CALENDAR_IDS")),
        allowed_attendee_emails={
            _normalize_email(email)
            for email in _split_env_list("WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS")
        },
    )
