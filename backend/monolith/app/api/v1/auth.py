from fastapi import APIRouter, HTTPException
from app.utils import fetch_query_to_scalar, fetch_query_to_df, ALGORITHM, SECRET_KEY, AsyncSessionLocal
from app.schemas import UserCreate, UserCreateOut, UserLogin, UserLoginOut
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.models import User

router = APIRouter(prefix="/api/v1", tags=["auth"])
salt = bcrypt.gensalt()

# зарегистрироваться
@router.post("/register", response_model=UserCreateOut)
async def create_user(params: UserCreate):
    try:
        email = params.email
        password = params.password
        existing_email = await fetch_query_to_scalar(
            "SELECT email FROM users WHERE email = :email",
            {"email": email},
        )
        if existing_email is not None:
            raise HTTPException(status_code=400, detail=f"Пользователь с email {email} уже зарегистрирован")
        if "@" not in email:
            raise HTTPException(status_code=400, detail="Неверный формат email")

        hash = bcrypt.hashpw(password.encode("utf-8"), salt)
        async with AsyncSessionLocal() as s:
            user = User(email=email, hash_password=hash.decode("utf-8"))
            s.add(user)
            await s.commit()

        user_id = await fetch_query_to_scalar("SELECT id FROM users WHERE email = :email", {"email": email})
        encoded_jwt = jwt.encode({"sub": user_id, "exp": datetime.now(tz=timezone.utc) + timedelta(days=1)}, SECRET_KEY, algorithm=ALGORITHM)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"user_id": user_id, "jwt": encoded_jwt}

# логин
@router.post("/login", response_model=UserLoginOut)
async def login_user(params: UserLogin):
    try:
        email = params.email
        password = params.password
        df = await fetch_query_to_df(
            "SELECT id, email, hash_password FROM users WHERE email = :email",
            {"email": email},
        )
        if df.empty:
            raise HTTPException(status_code=404, detail=f"Пользователь с email {email} не найден")

        hash = bytes(df["hash_password"].iloc[0], "utf-8")
        ok = bcrypt.checkpw(password.encode('utf-8'), hash)
        if not ok:
            raise HTTPException(status_code=401, detail="Неверный пароль")

        user_id = int(df["id"].iloc[0])
        encoded_jwt = jwt.encode({"sub": user_id, "exp": datetime.now(tz=timezone.utc) + timedelta(days=1)}, SECRET_KEY, algorithm=ALGORITHM)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"user_id": user_id, "jwt": encoded_jwt}