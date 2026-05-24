from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.database import get_db
from app.models import ApplicationStats
from app.schemas import ApplicationStatsOut

router = APIRouter(prefix="/api/v1/application-stats", tags=["applications"])

@router.get("/", response_model=List[ApplicationStatsOut])
async def get_application_stats(db: AsyncSession = Depends(get_db)):
    """Возвращает статистику по заявлениям по годам и специальностям."""
    statement = (
        select(ApplicationStats)
        .order_by(ApplicationStats.specialty_id, ApplicationStats.year)
    )
    result = await db.execute(statement)
    apps = result.scalars().all()
    return apps