"""Testes do histórico e ranking de Análises 360."""

from openjarvis.zeusex.analysis_360 import build_analysis_360
from openjarvis.zeusex.marketplace import PotentialSignals, ProductInput
from openjarvis.zeusex.report_store import AnalysisReportStore


def _report(name: str, score: str | None, profit_price: str = "100"):
    product = ProductInput(
        name=name,
        marketplace="shopee",
        sale_price=profit_price,
        product_cost="40",
    )
    signals = (
        PotentialSignals(
            demand=score,
            competition="0",
            margin=score,
            listing_quality=score,
        )
        if score is not None
        else None
    )
    return build_analysis_360(product, signals=signals)


def test_store_persists_json_and_markdown(tmp_path) -> None:
    store = AnalysisReportStore(tmp_path / "reports.db")
    saved = store.save(_report("Produto A", "80"))

    reloaded = AnalysisReportStore(tmp_path / "reports.db").get(saved.id)
    assert reloaded is not None
    assert reloaded.product_name == "Produto A"
    assert reloaded.report["profit"]["profit"] == "60.00"
    assert "# Análise 360" in reloaded.markdown


def test_top_products_prioritizes_explicit_potential_score(tmp_path) -> None:
    store = AnalysisReportStore(tmp_path / "reports.db")
    store.save(_report("Sem sinais", None, "200"))
    store.save(_report("Potencial médio", "60"))
    store.save(_report("Potencial alto", "90"))

    ranked = store.top_products()

    assert [item.product_name for item in ranked] == [
        "Potencial alto",
        "Potencial médio",
        "Sem sinais",
    ]


def test_top_products_can_filter_non_profitable_reports(tmp_path) -> None:
    store = AnalysisReportStore(tmp_path / "reports.db")
    store.save(_report("Lucrativo", "70", "100"))
    store.save(_report("Prejuízo", "95", "20"))

    assert [item.product_name for item in store.top_products()] == ["Lucrativo"]
    assert [item.product_name for item in store.top_products(profitable_only=False)] == [
        "Prejuízo",
        "Lucrativo",
    ]
