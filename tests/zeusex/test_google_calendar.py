from __future__ import annotations

from dataclasses import replace

import pytest

from openjarvis.zeusex.google_calendar import (
    CalendarAccessMode,
    CalendarConnectorStatus,
    CalendarEvent,
    GoogleCalendarConfig,
    GoogleCalendarService,
)
from openjarvis.zeusex.google_calendar_api import GoogleCalendarAPI


class FakeConnector:
    def __init__(self) -> None:
        self.created: list[CalendarEvent] = []

    def status(self) -> CalendarConnectorStatus:
        return CalendarConnectorStatus(
            enabled=True,
            access_mode="read_write",
            authenticated=True,
        )

    def list_events(self, **kwargs):
        return [
            CalendarEvent(
                id="1",
                title="Reunião ZeusExAI",
                start=kwargs["time_min"],
                end=kwargs["time_max"],
            )
        ]

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        created = replace(event, id="evt-123")
        self.created.append(created)
        return created


def test_integration_is_disabled_by_default() -> None:
    service = GoogleCalendarService()
    status = service.status()
    assert status.enabled is False
    with pytest.raises(PermissionError):
        service.list_events(
            time_min="2026-07-21T09:00:00-03:00",
            time_max="2026-07-21T10:00:00-03:00",
        )


def test_read_only_mode_lists_events_and_blocks_writes() -> None:
    service = GoogleCalendarService(
        FakeConnector(),
        GoogleCalendarConfig(enabled=True, access_mode=CalendarAccessMode.READ_ONLY),
    )
    events = service.list_events(
        time_min="2026-07-21T09:00:00-03:00",
        time_max="2026-07-21T10:00:00-03:00",
    )
    assert events[0].title == "Reunião ZeusExAI"
    with pytest.raises(PermissionError):
        service.create_event(events[0], confirmed=True)


def test_read_write_requires_explicit_confirmation() -> None:
    connector = FakeConnector()
    service = GoogleCalendarService(
        connector,
        GoogleCalendarConfig(enabled=True, access_mode=CalendarAccessMode.READ_WRITE),
    )
    event = CalendarEvent(
        id="pending",
        title="Planejamento",
        start="2026-07-21T09:00:00-03:00",
        end="2026-07-21T10:00:00-03:00",
    )
    with pytest.raises(PermissionError):
        service.create_event(event)
    created = service.create_event(event, confirmed=True)
    assert created.id == "evt-123"


def test_invalid_interval_is_rejected() -> None:
    service = GoogleCalendarService(
        FakeConnector(),
        GoogleCalendarConfig(enabled=True, access_mode=CalendarAccessMode.READ_ONLY),
    )
    with pytest.raises(ValueError):
        service.list_events(
            time_min="2026-07-21T10:00:00-03:00",
            time_max="2026-07-21T09:00:00-03:00",
        )


def test_api_exposes_status_and_read_operations() -> None:
    api = GoogleCalendarAPI(
        GoogleCalendarService(
            FakeConnector(),
            GoogleCalendarConfig(enabled=True, access_mode=CalendarAccessMode.READ_ONLY),
        )
    )
    status = api.dispatch("GET", "/v1/integrations/google-calendar/status")
    assert status.status == 200
    response = api.dispatch(
        "GET",
        "/v1/integrations/google-calendar/events",
        query={
            "time_min": "2026-07-21T09:00:00-03:00",
            "time_max": "2026-07-21T10:00:00-03:00",
        },
    )
    assert response.status == 200
    assert response.body["items"][0]["id"] == "1"


def test_api_blocks_creation_without_confirmation() -> None:
    api = GoogleCalendarAPI(
        GoogleCalendarService(
            FakeConnector(),
            GoogleCalendarConfig(enabled=True, access_mode=CalendarAccessMode.READ_WRITE),
        )
    )
    payload = {
        "title": "Reunião",
        "start": "2026-07-21T09:00:00-03:00",
        "end": "2026-07-21T10:00:00-03:00",
    }
    blocked = api.dispatch("POST", "/v1/integrations/google-calendar/events", payload)
    assert blocked.status == 403
    created = api.dispatch(
        "POST",
        "/v1/integrations/google-calendar/events",
        payload,
        confirmed=True,
    )
    assert created.status == 201


def test_preview_validates_locally_without_creating_event() -> None:
    connector = FakeConnector()
    api = GoogleCalendarAPI(GoogleCalendarService(connector))

    response = api.dispatch(
        "POST",
        "/v1/integrations/google-calendar/events/preview",
        {
            "title": "  Planejamento Zeus  ",
            "start": "2026-07-21T09:00:00-03:00",
            "end": "2026-07-21T10:00:00-03:00",
        },
    )

    assert response.status == 200
    assert response.body["preview"]["event"]["title"] == "Planejamento Zeus"
    assert response.body["preview"]["requires_confirmation"] is True
    assert response.body["preview"]["external_action_performed"] is False
    assert connector.created == []
