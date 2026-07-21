"""Biblioteca SQLite de modelos reutilizáveis de campanha."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from openjarvis.zeusex.campaigns import CampaignTemplate


@dataclass(frozen=True, slots=True)
class SavedCampaignTemplate:
    id: int
    template: CampaignTemplate


class CampaignTemplateStore:
    """Persiste apenas configuração editorial, nunca credenciais."""

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
                CREATE TABLE IF NOT EXISTS campaign_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    brand TEXT NOT NULL,
                    call_to_action TEXT NOT NULL,
                    include_price INTEGER NOT NULL
                )
                """
            )

    @staticmethod
    def _row(row: sqlite3.Row) -> SavedCampaignTemplate:
        return SavedCampaignTemplate(
            id=row["id"],
            template=CampaignTemplate(
                name=row["name"],
                brand=row["brand"],
                call_to_action=row["call_to_action"],
                include_price=bool(row["include_price"]),
            ),
        )

    def save(self, template: CampaignTemplate) -> SavedCampaignTemplate:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO campaign_templates(
                    name, brand, call_to_action, include_price
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    brand = excluded.brand,
                    call_to_action = excluded.call_to_action,
                    include_price = excluded.include_price
                """,
                (
                    template.name,
                    template.brand,
                    template.call_to_action,
                    int(template.include_price),
                ),
            )
            row = connection.execute(
                "SELECT * FROM campaign_templates WHERE name = ?",
                (template.name,),
            ).fetchone()
        return self._row(row)

    def get(self, name: str) -> SavedCampaignTemplate | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM campaign_templates WHERE name = ?",
                (name.strip(),),
            ).fetchone()
        return self._row(row) if row else None

    def list(self) -> list[SavedCampaignTemplate]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM campaign_templates ORDER BY name ASC"
            ).fetchall()
        return [self._row(row) for row in rows]


__all__ = ["CampaignTemplateStore", "SavedCampaignTemplate"]
