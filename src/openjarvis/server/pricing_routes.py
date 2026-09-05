"""Rotas locais do modo de precificação sem API de marketplace."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from openjarvis.zeusex.pricing_import import MAX_FILE_BYTES, import_pricing_products

router = APIRouter(prefix="/v1/pricing", tags=["pricing"])


@router.post("/import")
async def import_spreadsheet(file: UploadFile = File(...)) -> dict[str, object]:
    """Lê somente os dados da planilha; não acessa nem altera anúncios."""

    content = await file.read(MAX_FILE_BYTES + 1)
    try:
        products = import_pricing_products(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
    return {
        "products": products,
        "count": len(products),
        "mode": "manual",
        "external_actions": False,
    }


__all__ = ["router"]
