"""Importação local e limitada de produtos CSV/XLSX para precificação."""

from __future__ import annotations

from csv import DictReader, Sniffer
from io import BytesIO, StringIO
from pathlib import PurePosixPath
from re import match
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

MAX_FILE_BYTES = 5_000_000
MAX_UNCOMPRESSED_BYTES = 50_000_000
MAX_PRODUCTS = 1000
MAX_COLUMNS = 64
_XML_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _normalized_header(value: object) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    ascii_text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return "_".join(part for part in "".join(char if char.isalnum() else " " for char in ascii_text).split())


_ALIASES = {
    "sku": ("sku", "codigo", "codigo_sku"),
    "name": ("nome", "produto", "name", "titulo"),
    "productCost": ("custo", "custo_produto", "product_cost"),
    "packagingCost": ("embalagem", "custo_embalagem", "packaging_cost"),
    "operationalCost": ("outros_custos", "custo_operacional", "operational_cost"),
    "desiredMarginPercent": ("margem_desejada", "margem", "desired_margin_percent"),
    "promotionalMarginPercent": ("margem_promocional", "promotional_margin_percent"),
    "currentPrice": ("preco_atual", "preco", "sale_price", "current_price"),
}


def _map_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for index, source in enumerate(rows[:MAX_PRODUCTS]):
        normalized = {_normalized_header(key): value for key, value in source.items()}
        product: dict[str, Any] = {}
        for target, aliases in _ALIASES.items():
            product[target] = next((normalized[key] for key in aliases if key in normalized), "")
        if not str(product["sku"]).strip() or not str(product["name"]).strip():
            raise ValueError(f"Linha {index + 2}: informe SKU e nome.")
        products.append(product)
    if not products:
        raise ValueError("O arquivo não contém produtos.")
    return products


def _parse_csv(content: bytes) -> list[dict[str, Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    sample = text[:4096]
    try:
        dialect = Sniffer().sniff(sample, delimiters=",;")
    except Exception:
        dialect = "excel"
    return _map_rows(list(DictReader(StringIO(text), dialect=dialect)))


def _shared_strings(archive: ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read(path))
    return ["".join(node.text or "" for node in item.iter(f"{_XML_NS}t")) for item in root]


def _cell_column(reference: str) -> int:
    letters = (match(r"[A-Z]+", reference.upper()) or [""])[0]
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def _cell_value(cell: ElementTree.Element, shared: list[str]) -> Any:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{_XML_NS}t"))
    value_node = cell.find(f"{_XML_NS}v")
    raw = value_node.text if value_node is not None and value_node.text is not None else ""
    if cell_type == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return ""
    if cell_type in {"str", "e"}:
        return raw
    if cell_type == "b":
        return raw == "1"
    try:
        number = float(raw)
        return int(number) if number.is_integer() else number
    except ValueError:
        return raw


def _parse_xlsx(content: bytes) -> list[dict[str, Any]]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("A planilha descompactada excede o limite de segurança.")
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("A planilha contém caminhos inválidos.")
            sheet_path = "xl/worksheets/sheet1.xml"
            if sheet_path not in archive.namelist():
                raise ValueError("A primeira aba da planilha não foi encontrada.")
            shared = _shared_strings(archive)
            root = ElementTree.fromstring(archive.read(sheet_path))
    except (BadZipFile, ElementTree.ParseError) as exc:
        raise ValueError("Arquivo XLSX inválido ou corrompido.") from exc

    matrix: list[list[Any]] = []
    for row in root.iter(f"{_XML_NS}row"):
        if len(matrix) > MAX_PRODUCTS:
            break
        values: list[Any] = []
        for cell in row.findall(f"{_XML_NS}c"):
            column = _cell_column(cell.attrib.get("r", ""))
            if column < 0 or column >= MAX_COLUMNS:
                continue
            while len(values) <= column:
                values.append("")
            values[column] = _cell_value(cell, shared)
        if any(str(value).strip() for value in values):
            matrix.append(values)
    if len(matrix) < 2:
        raise ValueError("A planilha precisa ter cabeçalho e ao menos um produto.")
    headers = [str(value) for value in matrix[0]]
    return _map_rows([
        {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        for row in matrix[1:]
    ])


def import_pricing_products(filename: str, content: bytes) -> list[dict[str, Any]]:
    """Importa dados sem executar fórmulas, macros ou conteúdo externo."""

    if not content:
        raise ValueError("O arquivo está vazio.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("O arquivo excede o limite de 5 MB.")
    extension = PurePosixPath(filename).suffix.lower()
    if extension == ".csv":
        return _parse_csv(content)
    if extension == ".xlsx":
        return _parse_xlsx(content)
    raise ValueError("Formato não suportado. Use CSV ou XLSX.")


__all__ = ["import_pricing_products"]
