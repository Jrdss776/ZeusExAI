"""Testes do trabalhador automático da fila."""

from decimal import Decimal

from openjarvis.zeusex.analysis_queue import AnalysisQueue
from openjarvis.zeusex.analysis_worker import AnalysisWorker
from openjarvis.zeusex.marketplace_listings import ShopeeAdapter


def test_worker_processes_and_persists_result(tmp_path) -> None:
    queue = AnalysisQueue(tmp_path / "queue.db")
    job = queue.enqueue("shopee", {"item_id": 7})

    worker = AnalysisWorker(
        queue,
        {
            "shopee": lambda payload: ShopeeAdapter().normalize(
                {
                    "item_id": payload["item_id"],
                    "name": "Produto",
                    "price": Decimal("39.90"),
                }
            )
        },
    )
    outcome = worker.run_once()

    assert outcome.processed is True
    stored = queue.get(job.id)
    assert stored is not None
    assert stored.status == "completed"
    assert stored.result is not None
    assert stored.result["price"] == "39.90"


def test_worker_sanitizes_handler_failure_and_requeues(tmp_path) -> None:
    queue = AnalysisQueue(tmp_path / "queue.db")
    job = queue.enqueue("shopee", {"secret": "não vazar"})

    def fail(payload):
        raise RuntimeError(payload["secret"])

    outcome = AnalysisWorker(queue, {"shopee": fail}, max_attempts=2).run_once()

    assert outcome.job is not None
    assert outcome.job.status == "queued"
    assert outcome.job.error == "Falha controlada: RuntimeError."
    assert "não vazar" not in outcome.job.error


def test_worker_fails_job_without_handler(tmp_path) -> None:
    queue = AnalysisQueue(tmp_path / "queue.db")
    queue.enqueue("mercado_livre", {"id": "MLB1"})

    outcome = AnalysisWorker(queue, {}).run_once()

    assert outcome.job is not None
    assert outcome.job.status == "failed"


def test_worker_reports_empty_queue(tmp_path) -> None:
    outcome = AnalysisWorker(AnalysisQueue(tmp_path / "queue.db"), {}).run_once()

    assert outcome.processed is False
    assert outcome.job is None
