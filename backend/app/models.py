from sqlalchemy import String, Integer, ForeignKey, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime

# Many-to-Many: комплекты ЕГЭ и предметы
class ExamSetItem(Base):
    __tablename__ = "exam_set_items"
    set_id: Mapped[int] = mapped_column(ForeignKey("exam_sets.id"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), primary_key=True)

# Many-to-Many: специальности и комплекты ЕГЭ 
class SpecialtyExamSet(Base):
    __tablename__ = "specialty_exam_sets"
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"), primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("exam_sets.id"), primary_key=True)


# Направления науки (предметы)
class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    
    exam_stats: Mapped[list["ExamStats"]] = relationship(back_populates="subject", lazy="selectin")

# Комплекты ЕГЭ
class ExamSet(Base):
    __tablename__ = "exam_sets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    
    # связь с предметами
    subjects: Mapped[list["Subject"]] = relationship(secondary="exam_set_items", lazy="selectin")
    specialties: Mapped[list["Specialty"]] = relationship(secondary="specialty_exam_sets", back_populates="exam_sets", lazy="selectin")

# Специальности (направления подготовки)
class Specialty(Base):
    __tablename__ = "specialties"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    
    # связь с комплектами ЕГЭ
    exam_sets: Mapped[list["ExamSet"]] = relationship(secondary="specialty_exam_sets", back_populates="specialties", lazy="selectin")
    application_stats: Mapped[list["ApplicationStats"]] = relationship(back_populates="specialty", lazy="selectin")

# Рождаемость
class BirthRate(Base):
    __tablename__ = "birth_rate"
    year: Mapped[int] = mapped_column(primary_key=True)
    births: Mapped[int] = mapped_column(BigInteger)

# Статистика ЕГЭ по годам
class ExamStats(Base):
    __tablename__ = "exam_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    year: Mapped[int] = mapped_column(Integer)
    participants: Mapped[int] = mapped_column(Integer)
    
    subject: Mapped["Subject"] = relationship(back_populates="exam_stats")

# Статистика заявлений по годам
class ApplicationStats(Base):
    __tablename__ = "application_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"))
    year: Mapped[int] = mapped_column(Integer)
    applications: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kcp: Mapped[int | None] = mapped_column(Integer, nullable=True) # КЦП, кол-во бюджетных мест
    enrolled: Mapped[int | None] = mapped_column(Integer, nullable=True) # кол-во зачисленных
    
    specialty: Mapped["Specialty"] = relationship(back_populates="application_stats")

    __table_args__ = (
        UniqueConstraint("specialty_id", "year", name="uq_specialty_year_stats"),
    )

# Отчёты
class Report(Base):
    __tablename__ = "reports"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"))
    method_id: Mapped[int] = mapped_column(ForeignKey("forecast_methods.id"))
    start_year: Mapped[int] = mapped_column(Integer)
    current_year: Mapped[int] = mapped_column(Integer)
    end_year: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

# Методы прогнозирования
class ForecastMethod(Base):
    __tablename__ = "forecast_methods"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True) # для Backend
    name: Mapped[str] = mapped_column(String(100), unique=True) # для Frontend

    __table_args__ = (
        UniqueConstraint("slug", "name", name="uq_slug_name_forecast_methods"),
    )