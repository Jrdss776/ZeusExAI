from dataclasses import replace
import json

import pytest

from openjarvis.zeusex.productivity_audit import JsonlProductivityAudit
from openjarvis.zeusex.productivity_tasks import (
    ProductivityTask,
    ProductivityTaskConfig,
    ProductivityTaskService,
    TaskAccessMode,
)


class FakeTaskConnector:
    def __init__(self) -> None:
        self.tasks = [ProductivityTask("1", "Revisar agenda")]

    def list_tasks(self, *, max_results):
        return self.tasks[:max_results]

    def create_task(self, task):
        created = replace(task, id="2")
        self.tasks.append(created)
        return created

    def complete_task(self, task_id):
        return replace(next(task for task in self.tasks if task.id == task_id), completed=True)

    def delete_task(self, task_id):
        self.tasks = [task for task in self.tasks if task.id != task_id]


def test_tasks_are_disabled_by_default():
    with pytest.raises(PermissionError):
        ProductivityTaskService().list_tasks()


def test_complete_and_delete_require_specific_confirmation(tmp_path):
    connector = FakeTaskConnector()
    audit_path = tmp_path / "vampira-audit.jsonl"
    service = ProductivityTaskService(
        connector,
        ProductivityTaskConfig(True, TaskAccessMode.READ_WRITE),
        JsonlProductivityAudit(audit_path),
    )

    with pytest.raises(PermissionError, match="confirmação explícita"):
        service.complete("1")
    assert service.complete("1", confirmed=True).completed is True
    with pytest.raises(PermissionError, match="confirmação explícita"):
        service.delete("1")
    service.delete("1", confirmed=True)

    events = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert [event["decision"] for event in events] == ["blocked", "allowed", "blocked", "allowed"]
    assert all("Revisar agenda" not in json.dumps(event) for event in events)
