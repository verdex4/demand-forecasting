from fastapi import APIRouter, Depends, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import TestIn, TestOut
from app.services.testing import get_model_errors

router = APIRouter(prefix="/api/v1/model/errors", tags=["model_errors"])

# получить ошибки модели
@router.post("/", response_model=list[TestOut])
async def test_model(request: Request, payload: TestIn | None = Body(None), db: AsyncSession = Depends(get_db)):
    """Тестирует модель и выдаёт ошибки модели по wMAPE.
    
    methods - список методов прогнозирования

    Если тела запроса нет или methods пустой, будут выбраны все методы прогнозирования
    """
    methods = None
    if payload:
        methods = payload.methods

    errors = await get_model_errors(methods)

    return errors