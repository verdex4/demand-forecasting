import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import pandas as pd
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
if DATABASE_URL is None:
    raise ValueError("Переменная окружения DATABASE_URL не задана")
if SECRET_KEY is None:
    raise ValueError("Переменная окружения SECRET_KEY не задана")
if ALGORITHM is None:
    raise ValueError("Переменная окружения ALGORITHM не задана")

engine = create_async_engine(str(DATABASE_URL))
AsyncSessionLocal = async_sessionmaker(bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_user_id(token: str = Depends(oauth2_scheme)) -> int:
    exc = HTTPException(
            status_code=401,
            detail="Не удалось верифицировать JWT токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM] if ALGORITHM else None)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise exc
        user_id = int(user_id_str)
    except Exception:
        raise exc

    return user_id

class Base(DeclarativeBase):
    pass

async def session():
    async with AsyncSessionLocal() as session:
        yield session

async def fetch_query_to_df(query_str, params=None) -> pd.DataFrame:
    async with engine.connect() as conn:
        result = await conn.execute(text(query_str), params or {})
        rows = result.fetchall()
        columns = list(result.keys())
        df = pd.DataFrame(rows, columns=columns)
        
    return df

async def fetch_query_to_scalar(query_str, params=None):
    async with engine.connect() as conn:
        result = await conn.execute(text(query_str), params or {})
        return result.scalar()