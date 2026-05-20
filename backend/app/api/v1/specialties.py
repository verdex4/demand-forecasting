from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.database import get_db
from app.models import Specialty, ExamSet
from app.schemas import SpecialtyShortOut, SpecialtyOut

router = APIRouter(prefix="/api/v1/specialties", tags=["specialties"])

@router.get("/short", response_model=List[SpecialtyShortOut])
async def get_all_specialties_short(db: AsyncSession = Depends(get_db)):
    """Возвращает список специальностей с кодом и названием."""
    statement = (
        select(Specialty)
        .order_by(Specialty.code)
    )
    result = await db.execute(statement)
    specialties = result.scalars().all()
    return specialties

@router.get("/", response_model=List[SpecialtyOut])
async def get_all_specialties(db: AsyncSession = Depends(get_db)):
    """Возвращает список специальностей с полной информацией (комплекты ЕГЭ, заявления)."""
    statement = (
        select(Specialty)
        .options(
            selectinload(Specialty.exam_sets).selectinload(ExamSet.subjects),
            selectinload(Specialty.application_stats)
        )
        .order_by(Specialty.code)
    )
    result = await db.execute(statement)
    specialties = result.scalars().all()
    return specialties