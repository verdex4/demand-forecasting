from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, AsyncSessionLocal, fetch_query_to_df
from app.schemas import ReportCreate, ReportCreateOut, ReportOut
from typing import List
from app.services.forecast import make_forecast
from app.services.report import make_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# получить созданные отчёты
@router.get("/", response_model=List[ReportOut])
async def get_reports(db: AsyncSession = Depends(get_db)):
    query = """
        SELECT 
            r.*,
            s.code AS specialty_code,
            s.name AS specialty_name,
            m.name AS method_name
        FROM public.reports r
        LEFT JOIN public.specialties s ON r.specialty_id = s.id
        JOIN public.forecast_methods m ON r.method_id = m.id
    """
    reports_df = await fetch_query_to_df(query)
    if reports_df.empty:
        return []
    
    reports_df["specialty_full_name"] = reports_df["specialty_code"] + " " + reports_df["specialty_name"]
    reports_df = reports_df.sort_values("created_at", ascending=False).reset_index(drop=True)
    
    return reports_df.to_dict(orient="records")

# создать отчёт
@router.post("/", response_model=ReportCreateOut)
async def create_report(request: Request, params: ReportCreate, db: AsyncSession = Depends(get_db)):
    """Создаёт отчёт по указанным параметрам.
    
    Доступные методы:
    * Последнее значение
    * Скользящее среднее за n лет (года, год)
    * Демографический метод (поправка на рождаемость)
    * Экспоненциальное сглаживание
    """
    try:
        df = await make_forecast(params.method, params.history_range, params.forecast_range)
        async with AsyncSessionLocal() as async_session:
            report_url = await make_report(
                df,
                params.input_specialty,
                params.method,
                params.history_range,
                params.forecast_range,
                async_session)
        return {"success": True, "report_url": report_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))