"""Testes da importação local de CSV e Excel."""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from openjarvis.zeusex.pricing_import import import_pricing_products


def _xlsx() -> bytes:
    output = BytesIO()
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>SKU</t></is></c><c r="B1" t="inlineStr"><is><t>Nome</t></is></c><c r="C1" t="inlineStr"><is><t>Custo</t></is></c></row>
<row r="2"><c r="A2" t="inlineStr"><is><t>X1</t></is></c><c r="B2" t="inlineStr"><is><t>Produto X</t></is></c><c r="C2"><v>39.9</v></c></row>
</sheetData></worksheet>"""
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


def test_imports_brazilian_csv() -> None:
    products = import_pricing_products(
        "produtos.csv",
        "SKU;Nome;Custo;Preço atual\nA1;Produto A;25,90;49,90".encode(),
    )

    assert products[0]["sku"] == "A1"
    assert products[0]["productCost"] == "25,90"
    assert products[0]["currentPrice"] == "49,90"


def test_imports_first_xlsx_sheet_without_external_library() -> None:
    products = import_pricing_products("produtos.xlsx", _xlsx())

    assert products == [{
        "sku": "X1", "name": "Produto X", "productCost": 39.9,
        "packagingCost": "", "operationalCost": "",
        "desiredMarginPercent": "", "promotionalMarginPercent": "",
        "currentPrice": "",
    }]


def test_rejects_missing_sku() -> None:
    with pytest.raises(ValueError, match="SKU e nome"):
        import_pricing_products("produtos.csv", b"SKU,Nome,Custo\n,Produto,10")


def test_rejects_unsupported_or_empty_file() -> None:
    with pytest.raises(ValueError, match="vazio"):
        import_pricing_products("produtos.csv", b"")
    with pytest.raises(ValueError, match="CSV ou XLSX"):
        import_pricing_products("produtos.xls", b"legacy")


def test_rejects_oversized_file() -> None:
    with pytest.raises(ValueError, match="5 MB"):
        import_pricing_products("produtos.csv", b"x" * 5_000_001)
