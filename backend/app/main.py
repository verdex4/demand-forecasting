from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy import select
from app.database import engine, Base, AsyncSessionLocal
import app.models as models
from app.seed import parse_excel, fill_specialties, fill_subjects_sets_apps, fill_births, fill_exams
import asyncio
from app.api.v1 import specialties

@asynccontextmanager
async def lifespan(app: FastAPI):
    # создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # проверяем, есть ли данные в базе
    async with AsyncSessionLocal() as async_session:
        result = await async_session.execute(select(models.ApplicationStats).limit(1))
        is_empty = result.scalar_one_or_none() is None

        if is_empty:
            print("База данных пуста. Импортируем данные из Excel...")
            df_spec, df_apps, df_births, df_exams = await asyncio.to_thread(parse_excel)
            await fill_specialties(df_spec, async_session)
            await fill_subjects_sets_apps(df_apps, async_session)
            await fill_births(df_births, async_session)
            await fill_exams(df_exams, async_session)
            await async_session.commit()
            print("Импорт успешно завершен.")
        else:
            print("База данных уже содержит данные. Пропуск импорта.")

    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello": "World"}

app.include_router(specialties.router, prefix="/api/v1")