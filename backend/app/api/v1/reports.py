from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ReportCreate, ReportOut
from typing import Tuple
from app.services.forecast import make_forecast
from app.services.report import make_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

@router.post("/", response_model=ReportOut)
async def create_report(request: Request, params: ReportCreate, db: AsyncSession = Depends(get_db)):
    try:
        df = await make_forecast("all", "sma_3", params.history_range, params.forecast_range)
        filename = await make_report(df, params.input_specialty, params.history_range, params.forecast_range)
        report_url = f"{request.base_url}reports/{filename}"
        return {"success": True, "report_url": report_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))