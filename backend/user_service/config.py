import os
from dotenv import load_dotenv

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