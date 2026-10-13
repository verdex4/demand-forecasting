from config import DATABASE_URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
import pandas as pd

engine = create_async_engine(str(DATABASE_URL))
AsyncSessionLocal = async_sessionmaker(bind=engine)

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