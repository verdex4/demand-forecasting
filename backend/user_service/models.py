from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase,Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200))
    hash_password: Mapped[str] = mapped_column(String(200))