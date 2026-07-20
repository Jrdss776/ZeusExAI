"""Testes da fila persistente de análises comerciais."""

import pytest

from openjarvis.zeusex.analysis_queue import AnalysisQueue


def test_queue_persists_and_claims_in_fifo_order(tmp_path) -> None:
    path = tmp_path / "queue.db"
    queue = AnalysisQueue(path)
    first = queue.enqueue("shopee", {"item_id": 1})
    queue.enqueue("mercado livre", {"id": "MLB1"})

    reloaded = AnalysisQueue(path)
    claimed = reloaded.claim_next()

    assert claimed is not None
    assert claimed.id == first.id
    assert claimed.status == "processing"
    assert claimed.attempts == 1


def test_queue_completes_job(tmp_path) -> None:
    queue = AnalysisQueue(tmp_path / "queue.db")
    job = queue.enqueue("shopee", {"item_id": 1})
    claimed = queue.claim_next()

    assert claimed is not None
    completed = queue.complete(job.id)
    assert completed.status == "completed"
    assert completed.error is None


def test_failure_requeues_until_attempt_limit(tmp_path) -> None:
    queue = AnalysisQueue(tmp_path / "queue.db")
    job = queue.enqueue("shopee", {"item_id": 1})

    queue.claim_next()
    retried = queue.fail(job.id, "temporário", max_attempts=2)
    assert retried.status == "queued"

    queue.claim_next()
    failed = queue.fail(job.id, "definitivo", max_attempts=2)
    assert failed.status == "failed"
    assert failed.error == "definitivo"


def test_queue_rejects_non_json_payload(tmp_path) -> None:
    queue = AnalysisQueue(tmp_path / "queue.db")

    with pytest.raises(ValueError, match="JSON"):
        queue.enqueue("shopee", {"invalid": object()})
