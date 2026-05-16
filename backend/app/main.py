from fastapi import FastAPI, Request
from sqlalchemy import select
import asyncio
from app.database import engine, Base, AsyncSessionLocal
from contextlib import asynccontextmanager
import app.models as models
from app.seed import seed
from app.api.v1 import specialties
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.settings import STATIC_DIR, TEMPLATES_DIR

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
            await seed(async_session)
            print("Импорт успешно завершен.")
        else:
            print("База данных уже содержит данные. Пропуск импорта.")

    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/employee")
async def employee(request: Request):
    return templates.TemplateResponse(request, "employee.html")

@app.get("/applicant")
async def applicant(request: Request):
    return templates.TemplateResponse(request, "applicant.html")

app.include_router(specialties.router, prefix="/api/v1")