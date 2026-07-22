"""Histórico local e ranking auditável das Análises 360."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import sqlite3

from openjarvis.zeusex.analysis_360 import Analysis360Report


@dataclass(frozen=True, slots=True)
class SavedAnalysis:
    id: int
    product_name: str
    marketplace: str
    profit: Decimal
    margin_percent: Decimal
    potential_score: Decimal | None
    report: dict[str, object]
    markdown: str
    created_at: str


class AnalysisReportStore:
    """Persiste relatórios sem credenciais, tokens ou chamadas externas."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_analysis_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    marketplace TEXT NOT NULL,
                    profit TEXT NOT NULL,
                    margin_percent TEXT NOT NULL,
                    potential_score TEXT,
                    report_json TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _row(row: sqlite3.Row) -> SavedAnalysis:
        score = row["potential_score"]
        return SavedAnalysis(
            id=row["id"],
            product_name=row["product_name"],
            marketplace=row["marketplace"],
            profit=Decimal(row["profit"]),
            margin_percent=Decimal(row["margin_percent"]),
            potential_score=Decimal(score) if score is not None else None,
            report=json.loads(row["report_json"]),
            markdown=row["markdown"],
            created_at=row["created_at"],
        )

    def save(self, report: Analysis360Report) -> SavedAnalysis:
        product = report.profit.product
        score = str(report.potential.score) if report.potential is not None else None
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO marketplace_analysis_reports(
                    product_name, marketplace, profit, margin_percent,
                    potential_score, report_json, markdown, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.name,
                    product.marketplace,
                    str(report.profit.profit),
                    str(report.profit.margin_percent),
                    score,
                    report.to_json(indent=0),
                    report.to_markdown(),
                    created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM marketplace_analysis_reports WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row(row)

    def get(self, report_id: int) -> SavedAnalysis | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM marketplace_analysis_reports WHERE id = ?",
                (report_id,),
            ).fetchone()
        return self._row(row) if row else None

    def list(self, *, limit: int = 100) -> list[SavedAnalysis]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM marketplace_analysis_reports
                ORDER BY id DESC LIMIT ?
                """,
                (max(1, min(limit, 1000)),),
            ).fetchall()
        return [self._row(row) for row in rows]

    def top_products(
        self,
        *,
        limit: int = 10,
        profitable_only: bool = True,
    ) -> list[SavedAnalysis]:
        conditions = "WHERE CAST(profit AS REAL) > 0" if profitable_only else ""
        query = f"""
            SELECT * FROM marketplace_analysis_reports
            {conditions}
            ORDER BY
                potential_score IS NULL ASC,
                CAST(potential_score AS REAL) DESC,
                CAST(profit AS REAL) DESC,
                id DESC
            LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(
                query,
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [self._row(row) for row in rows]


__all__ = ["AnalysisReportStore", "SavedAnalysis"]
