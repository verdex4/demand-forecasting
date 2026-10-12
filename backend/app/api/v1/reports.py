from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, AsyncSessionLocal, fetch_query_to_df, fetch_query_to_scalar
from app.schemas import ReportCreate, ReportCreateOut, ReportListOut,ReportOut
from typing import List
from app.services.forecast import make_forecast
from app.services.report import make_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# получить список созданныъ отчётов
@router.get("/", response_model=List[ReportListOut])
async def get_reports(db: AsyncSession = Depends(get_db)):
    try:
        query = """
            SELECT
                s.code AS specialty_code,
                s.name AS specialty_name,
                m.name AS method_name,
                r.id AS id,
                r.start_year AS start_year,
                r.current_year AS current_year,
                r.end_year AS end_year,
                r.created_at AS created_at
            FROM public.reports r
            LEFT JOIN public.specialties s ON r.specialty_id = s.id
            JOIN public.forecast_methods m ON r.method_id = m.id
        """
        df = await fetch_query_to_df(query)
        if df.empty:
            return []
        
        df["specialty_full_name"] = df["specialty_code"] + " " + df["specialty_name"]
        df = df.sort_values(by=["id", "created_at"], ascending=[True, False]).reset_index(drop=True)
        df = df[["id", "specialty_full_name", "method_name", "start_year", "current_year", "end_year"]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return df.to_dict(orient="records")

# получить отчёт
@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    query = """
        SELECT
            r.html_content
        FROM public.reports r
        WHERE r.id = :report_id
    """
    html_content = await fetch_query_to_scalar(query, {"report_id": report_id})
    if not html_content:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {"html_content": html_content}

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
        df_demand, table_map = await make_forecast(
            params.input_specialty,
            params.method, params.history_range, params.forecast_range,
            params.kcp_manual, params.kcp_growth_pct,
            params.paid_manual, params.paid_growth_pct
        )

        async with AsyncSessionLocal() as async_session:
            await make_report(
                df_demand,
                table_map,
                params.input_specialty,
                params.method,
                params.history_range,
                params.forecast_range,
                async_session)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))