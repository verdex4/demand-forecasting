import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import pandas as pd

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(str(DATABASE_URL))

AsyncSessionLocal = async_sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def fetch_query_to_df(query_str, params=None) -> pd.DataFrame:
    async with engine.connect() as conn:
        result = await conn.execute(text(query_str), params or {})
        rows = result.fetchall()
        columns = list(result.keys())
        df = pd.DataFrame(rows, columns=columns)
        
    return df