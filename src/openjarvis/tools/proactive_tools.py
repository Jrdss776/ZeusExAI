# ruff: noqa: E501
"""Proactive agent tools — check/record permissions, queue and execute actions.

These tools are used exclusively by ``ProactiveAgent`` to manage the
propose → approve → execute lifecycle for autonomous actions.

Permission key convention: ``"{action_type}:{context_key}"``

Approval response parsing
-------------------------
When the user replies to a pending-actions notification, their message is
expected to contain one or more tokens of the form:

    ``{action_id} yes``   or   ``{action_id} no``
    ``yes {action_id}``   or   ``no {action_id}``
    ``always yes {action_id}``  →  approve + remember
    ``always no {action_id}``   →  deny + remember
    ``yes all``  /  ``no all``  →  bulk approve/deny all pending

Call ``parse_approval_response(text, store)`` from any channel message handler
to process these replies without running the full agent.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._stubs import BaseTool, ToolSpec
from openjarvis.tools.approval_store import (
    DECISION_ALWAYS_APPROVE,
    DECISION_ALWAYS_DENY,
    STATUS_APPROVED,
    STATUS_DENIED,
    STATUS_EXECUTED,
    TIER_HIGH,
    TIER_LOW,
    TIER_MEDIUM,
    TIER_TRIVIAL,
    ApprovalStore,
    PendingAction,
)

# ---------------------------------------------------------------------------
# Shared store (lazily initialised, one per process)
# ---------------------------------------------------------------------------

_store: Optional[ApprovalStore] = None


def get_store() -> ApprovalStore:
    global _store
    if _store is None:
        _store = ApprovalStore()
    return _store


# ---------------------------------------------------------------------------
# check_permission
# ---------------------------------------------------------------------------


@ToolRegistry.register("check_permission")
class CheckPermissionTool(BaseTool):
    """Look up whether the user has a remembered decision for a permission key."""

    tool_id = "check_permission"

    def __init__(self, store: Optional[ApprovalStore] = None) -> None:
        self._store = store

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="check_permission",
            description=(
                "Check whether the user has a remembered permission decision for "
                "an action pattern. Returns 'always_approve', 'always_deny', or 'unknown'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "permission_key": {
                        "type": "string",
                        "description": (
                            "Permission pattern key, e.g. "
                            "'email_delete:domain:noreply.github.com'"
                        ),
                    },
                },
                "required": ["permission_key"],
            },
            category="proactive",
        )

    def execute(self, **params: Any) -> ToolResult:
        key = params.get("permission_key", "")
        store = self._store or get_store()
        rule = store.get_permission(key)
        decision = rule.decision if rule else "unknown"
        return ToolResult(
            tool_name=self.spec.name,
            success=True,
            content=decision,
            metadata={"permission_key": key, "decision": decision},
        )


# ---------------------------------------------------------------------------
# queue_action
# ---------------------------------------------------------------------------


@ToolRegistry.register("queue_action")
class QueueActionTool(BaseTool):
    """Queue a proposed action for user approval or immediate execution."""

    tool_id = "queue_action"

    def __init__(self, store: Optional[ApprovalStore] = None) -> None:
        self._store = store

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="queue_action",
            description=(
                "Queue a proposed action. Tier controls whether user approval is required:\n"
                f"  '{TIER_TRIVIAL}' — execute immediately, no approval needed\n"
                f"  '{TIER_LOW}'     — ask once per pattern, then remember\n"
                f"  '{TIER_MEDIUM}'  — ask each time unless user said 'always'\n"
                f"  '{TIER_HIGH}'    — always ask, never auto-remember\n"
                "Returns the action_id so you can reference it in notifications. "
                "Supported productivity actions and payloads: "
                "email_send={recipients:[email],subject,body}; "
                "calendar_create={summary,start,end,calendar_id?,location?,description?,attendees?}; "
                "task_create={title,notes?,due?,task_list_id?}; "
                "task_complete/task_delete={task_id,task_list_id?}; "
                "local_process_close={pid,expected_name}; "
                "local_organize_folder={path,snapshot_hash}. "
                "Local computer actions must use tier='high' and are executed only "
                "after explicit approval in the desktop bell."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "description": "Short slug, e.g. 'email_delete', 'sms_draft_reply'.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of what will be done.",
                    },
                    "payload": {
                        "type": "object",
                        "description": "JSON payload the executor will use to carry out the action.",
                    },
                    "permission_key": {
                        "type": "string",
                        "description": "Pattern key for permission memory lookup.",
                    },
                    "tier": {
                        "type": "string",
                        "enum": [TIER_TRIVIAL, TIER_LOW, TIER_MEDIUM, TIER_HIGH],
                        "description": "Approval tier.",
                    },
                },
                "required": [
                    "action_type",
                    "description",
                    "payload",
                    "permission_key",
                    "tier",
                ],
            },
            category="proactive",
        )

    def execute(self, **params: Any) -> ToolResult:
        store = self._store or get_store()
        action = store.queue_action(
            action_type=params["action_type"],
            description=params["description"],
            payload=params.get("payload", {}),
            permission_key=params["permission_key"],
            tier=params["tier"],
        )
        return ToolResult(
            tool_name=self.spec.name,
            success=True,
            content=action.id,
            metadata={"action_id": action.id, "status": action.status},
        )


# ---------------------------------------------------------------------------
# get_pending_actions
# ---------------------------------------------------------------------------


@ToolRegistry.register("get_pending_actions")
class GetPendingActionsTool(BaseTool):
    """Return all pending (not yet decided) actions as a JSON list."""

    tool_id = "get_pending_actions"

    def __init__(self, store: Optional[ApprovalStore] = None) -> None:
        self._store = store

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="get_pending_actions",
            description="Return all pending actions awaiting user approval as a JSON list.",
            parameters={"type": "object", "properties": {}},
            category="proactive",
        )

    def execute(self, **params: Any) -> ToolResult:
        store = self._store or get_store()
        store.expire_stale()
        actions = store.list_pending()
        data = [
            {
                "id": a.id,
                "action_type": a.action_type,
                "description": a.description,
                "tier": a.tier,
                "permission_key": a.permission_key,
                "created_at": a.created_at,
            }
            for a in actions
        ]
        return ToolResult(
            tool_name=self.spec.name,
            success=True,
            content=json.dumps(data, indent=2),
            metadata={"count": len(data)},
        )


# ---------------------------------------------------------------------------
# record_decision
# ---------------------------------------------------------------------------


@ToolRegistry.register("record_decision")
class RecordDecisionTool(BaseTool):
    """Record a user approval or denial for a queued action."""

    tool_id = "record_decision"

    def __init__(self, store: Optional[ApprovalStore] = None) -> None:
        self._store = store

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="record_decision",
            description=(
                "Record the user's approval or denial for a pending action. "
                "Set remember=true to save the decision to permission memory so "
                "the same pattern is handled automatically in future."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action_id": {
                        "type": "string",
                        "description": "The action_id returned by queue_action.",
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "True to approve, false to deny.",
                    },
                    "remember": {
                        "type": "boolean",
                        "description": "Save decision to permission memory for this pattern.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional note to store alongside the permission rule.",
                    },
                },
                "required": ["action_id", "approved"],
            },
            category="proactive",
        )

    def execute(self, **params: Any) -> ToolResult:
        store = self._store or get_store()
        action_id = params["action_id"]
        approved = bool(params.get("approved", False))
        remember = bool(params.get("remember", False))
        notes = params.get("notes", "")

        action = store.get_action(action_id)
        if action is None:
            return ToolResult(
                tool_name=self.spec.name,
                success=False,
                content=f"Action not found: {action_id}",
            )

        new_status = STATUS_APPROVED if approved else STATUS_DENIED
        store.update_status(action_id, new_status)

        if remember:
            decision = DECISION_ALWAYS_APPROVE if approved else DECISION_ALWAYS_DENY
            store.set_permission(
                action.permission_key,
                decision,
                approved=approved,
                notes=notes,
            )

        msg = f"Action {action_id} {'approved' if approved else 'denied'}."
        if remember:
            msg += f" Permission '{action.permission_key}' saved as {decision}."
        return ToolResult(
            tool_name=self.spec.name,
            success=True,
            content=msg,
            metadata={
                "action_id": action_id,
                "approved": approved,
                "remembered": remember,
            },
        )


# ---------------------------------------------------------------------------
# execute_pending_actions
# ---------------------------------------------------------------------------


@ToolRegistry.register("execute_pending_actions")
class ExecutePendingActionsTool(BaseTool):
    """Execute all approved (or trivial) actions and return a summary."""

    tool_id = "execute_pending_actions"

    def __init__(
        self,
        store: Optional[ApprovalStore] = None,
        executor_fn: Optional[Any] = None,
    ) -> None:
        self._store = store
        # executor_fn(action: PendingAction) -> (success: bool, message: str)
        self._executor_fn = executor_fn

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="execute_pending_actions",
            description=(
                "Execute all approved actions in the queue. "
                "Returns a JSON summary of what succeeded and what failed."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific action IDs to execute. "
                        "If omitted, executes all approved actions.",
                    },
                },
            },
            category="proactive",
        )

    def execute(self, **params: Any) -> ToolResult:
        store = self._store or get_store()
        action_ids: Optional[List[str]] = params.get("action_ids")

        if action_ids:
            actions = [a for a in store.list_approved() if a.id in set(action_ids)]
        else:
            actions = store.list_approved()

        results: List[Dict[str, Any]] = []
        for action in actions:
            success, message = self._run_action(action)
            if success:
                store.update_status(action.id, STATUS_EXECUTED)
            results.append(
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "description": action.description,
                    "success": success,
                    "message": message,
                }
            )

        return ToolResult(
            tool_name=self.spec.name,
            success=True,
            content=json.dumps(results, indent=2),
            metadata={"executed": len(results)},
        )

    def _run_action(self, action: PendingAction) -> Tuple[bool, str]:
        if self._executor_fn is not None:
            try:
                return self._executor_fn(action)
            except Exception as exc:
                return False, str(exc)

        # Built-in dispatcher — extend as connectors grow
        payload = action.payload
        atype = action.action_type

        try:
            if atype == "email_delete":
                return _exec_email_delete(payload)
            if atype == "email_archive":
                return _exec_email_archive(payload)
            if atype == "email_send":
                return _exec_email_send(payload)
            if atype == "sms_send":
                return _exec_sms_send(payload)
            if atype == "sms_draft_reply":
                # Draft only — surface in next digest, don't send
                return True, f"Draft saved: {payload.get('draft', '')[:80]}"
            if atype == "calendar_decline":
                return _exec_calendar_decline(payload)
            if atype == "calendar_accept":
                return _exec_calendar_accept(payload)
            if atype == "calendar_create":
                return _exec_calendar_create(payload)
            if atype == "task_create":
                return _exec_task_create(payload)
            if atype == "task_complete":
                return _exec_task_complete(payload)
            if atype == "task_delete":
                return _exec_task_delete(payload)
            if atype == "local_process_close":
                return _exec_local_process_close(payload)
            if atype == "local_organize_folder":
                return _exec_local_organize_folder(payload)
            return False, f"No executor registered for action_type '{atype}'"
        except Exception as exc:
            return False, str(exc)


# ---------------------------------------------------------------------------
# Built-in action executors (thin wrappers around connector/channel APIs)
# ---------------------------------------------------------------------------


def _exec_email_delete(payload: Dict[str, Any]) -> Tuple[bool, str]:
    msg_id = payload.get("message_id", "")
    if not msg_id:
        return False, "Missing message_id in payload"
    try:
        from openjarvis.connectors.gmail import GmailConnector

        conn = GmailConnector()
        conn.delete_message(msg_id)
        return True, f"Deleted email {msg_id}"
    except Exception as exc:
        return False, str(exc)


def _exec_email_archive(payload: Dict[str, Any]) -> Tuple[bool, str]:
    msg_id = payload.get("message_id", "")
    if not msg_id:
        return False, "Missing message_id in payload"
    try:
        from openjarvis.connectors.gmail import GmailConnector

        conn = GmailConnector()
        conn.archive_message(msg_id)
        return True, f"Archived email {msg_id}"
    except Exception as exc:
        return False, str(exc)


def _exec_email_send(payload: Dict[str, Any]) -> Tuple[bool, str]:
    recipients = payload.get("recipients") or []
    if isinstance(recipients, str):
        recipients = [recipients]
    try:
        from openjarvis.connectors.gmail import GmailConnector

        result = GmailConnector().send_message(
            recipients,
            str(payload.get("subject") or ""),
            str(payload.get("body") or ""),
        )
        return True, f"Sent email {result.get('id', '')}".strip()
    except Exception as exc:
        return False, str(exc)


def _exec_sms_send(payload: Dict[str, Any]) -> Tuple[bool, str]:
    contact = payload.get("contact", "")
    body = payload.get("body", "")
    if not contact or not body:
        return False, "Missing contact or body in payload"
    try:
        from openjarvis.channels.imessage_daemon import send_imessage

        send_imessage(contact, body)
        return True, f"Sent iMessage to {contact}"
    except Exception as exc:
        return False, str(exc)


def _exec_calendar_decline(payload: Dict[str, Any]) -> Tuple[bool, str]:
    event_id = payload.get("event_id", "")
    calendar_id = payload.get("calendar_id", "primary")
    if not event_id:
        return False, "Missing event_id in payload"
    try:
        from openjarvis.connectors.gcalendar import GCalendarConnector

        conn = GCalendarConnector()
        conn.decline_event(event_id, calendar_id=calendar_id)
        return True, f"Declined calendar event {event_id}"
    except Exception as exc:
        return False, str(exc)


def _exec_calendar_accept(payload: Dict[str, Any]) -> Tuple[bool, str]:
    event_id = payload.get("event_id", "")
    calendar_id = payload.get("calendar_id", "primary")
    if not event_id:
        return False, "Missing event_id in payload"
    try:
        from openjarvis.connectors.gcalendar import GCalendarConnector

        conn = GCalendarConnector()
        conn.accept_event(event_id, calendar_id=calendar_id)
        return True, f"Accepted calendar event {event_id}"
    except Exception as exc:
        return False, str(exc)


def _exec_calendar_create(payload: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        from openjarvis.connectors.gcalendar import GCalendarConnector

        result = GCalendarConnector().create_event(
            summary=str(payload.get("summary") or payload.get("title") or ""),
            start=str(payload.get("start") or ""),
            end=str(payload.get("end") or ""),
            calendar_id=str(payload.get("calendar_id") or "primary"),
            location=str(payload.get("location") or ""),
            description=str(payload.get("description") or ""),
            attendees=payload.get("attendees") or [],
            time_zone=str(payload.get("time_zone") or ""),
        )
        return True, f"Created calendar event {result.get('id', '')}".strip()
    except Exception as exc:
        return False, str(exc)


def _exec_task_create(payload: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        from openjarvis.connectors.google_tasks import GoogleTasksConnector

        result = GoogleTasksConnector().create_task(
            str(payload.get("title") or ""),
            notes=str(payload.get("notes") or ""),
            due=str(payload.get("due") or ""),
            task_list_id=str(payload.get("task_list_id") or "@default"),
        )
        return True, f"Created task {result.get('id', '')}".strip()
    except Exception as exc:
        return False, str(exc)


def _exec_task_complete(payload: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        from openjarvis.connectors.google_tasks import GoogleTasksConnector

        result = GoogleTasksConnector().complete_task(
            str(payload.get("task_id") or ""),
            task_list_id=str(payload.get("task_list_id") or "@default"),
        )
        return True, f"Completed task {result.get('id', '')}".strip()
    except Exception as exc:
        return False, str(exc)


def _exec_task_delete(payload: Dict[str, Any]) -> Tuple[bool, str]:
    task_id = str(payload.get("task_id") or "")
    try:
        from openjarvis.connectors.google_tasks import GoogleTasksConnector

        GoogleTasksConnector().delete_task(
            task_id,
            task_list_id=str(payload.get("task_list_id") or "@default"),
        )
        return True, f"Deleted task {task_id}"
    except Exception as exc:
        return False, str(exc)


def _exec_local_process_close(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Gracefully close one process whose PID/name were shown for approval."""

    try:
        pid = int(payload.get("pid", 0))
    except (TypeError, ValueError):
        return False, "Invalid pid in payload"
    expected_name = str(payload.get("expected_name") or "").strip()
    from openjarvis.tools.pc_control import execute_graceful_process_close

    return execute_graceful_process_close(pid, expected_name)


def _exec_local_organize_folder(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Apply a previously previewed folder plan after desktop approval."""

    path = str(payload.get("path") or "").strip()
    snapshot_hash = str(payload.get("snapshot_hash") or "").strip()
    if not path or not snapshot_hash:
        return False, "Missing path or snapshot_hash in payload"
    from openjarvis.tools.pc_control import execute_folder_organization

    return execute_folder_organization(path, snapshot_hash)


# ---------------------------------------------------------------------------
# Approval response parser (for channel message handlers)
# ---------------------------------------------------------------------------

# Matches: "abc123 yes", "yes abc123", "always yes abc123", "yes all", etc.
_APPROVAL_RE = re.compile(
    r"\b(?P<always>always\s+)?(?P<decision>yes|no|approve|deny)\s+(?P<target>[a-f0-9]{12}|all)\b"
    r"|"
    r"\b(?P<target2>[a-f0-9]{12}|all)\s+(?P<always2>always\s+)?(?P<decision2>yes|no|approve|deny)\b",
    re.IGNORECASE,
)


def parse_approval_response(
    text: str,
    store: Optional[ApprovalStore] = None,
) -> List[Dict[str, Any]]:
    """Parse a free-text message for approval tokens and update the store.

    Returns a list of dicts describing each decision that was processed,
    for use in an acknowledgement message back to the user.

    Call this from any channel message handler before routing the message
    to the main agent, e.g. inside the iMessage daemon or Telegram bot.
    """
    s = store or get_store()
    processed: List[Dict[str, Any]] = []

    # Notification template displays ids as `[abc123]`; users naturally reply
    # with `{abc123} yes`, `(abc123) yes`, etc.  Strip those surrounding
    # brackets/braces/parens before regex matching so the word-boundary
    # check sees a clean id.
    text = re.sub(r"[\[\]\{\}\(\)]", " ", text)

    for m in _APPROVAL_RE.finditer(text):
        target = (m.group("target") or m.group("target2") or "").lower()
        raw_decision = (m.group("decision") or m.group("decision2") or "").lower()
        always = bool(m.group("always") or m.group("always2"))

        approved = raw_decision in ("yes", "approve")

        if target == "all":
            pending = s.list_pending()
            for action in pending:
                new_status = STATUS_APPROVED if approved else STATUS_DENIED
                s.update_status(action.id, new_status)
                if always and action.tier in (TIER_LOW, TIER_MEDIUM):
                    decision = (
                        DECISION_ALWAYS_APPROVE if approved else DECISION_ALWAYS_DENY
                    )
                    s.set_permission(action.permission_key, decision, approved=approved)
                processed.append(
                    {"id": action.id, "approved": approved, "remembered": always}
                )
        else:
            action = s.get_action(target)
            if action is None:
                continue
            new_status = STATUS_APPROVED if approved else STATUS_DENIED
            s.update_status(target, new_status)
            remember = always and action.tier in (TIER_LOW, TIER_MEDIUM)
            if remember:
                decision = DECISION_ALWAYS_APPROVE if approved else DECISION_ALWAYS_DENY
                s.set_permission(action.permission_key, decision, approved=approved)
            processed.append(
                {"id": target, "approved": approved, "remembered": remember}
            )

    return processed


__all__ = [
    "CheckPermissionTool",
    "ExecutePendingActionsTool",
    "GetPendingActionsTool",
    "QueueActionTool",
    "RecordDecisionTool",
    "get_store",
    "parse_approval_response",
]
