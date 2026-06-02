from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator
from typing import List, Optional, Tuple


# 1. СХЕМЫ ДЛЯ ПРЕДМЕТОВ (Subjects)
class SubjectBase(BaseModel):
    """Базовая схема для предмета."""
    name: str

class SubjectOut(SubjectBase):
    """Схема для получения предмета."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class SubjectCreate(SubjectBase):
    """Схема для создания нового предмета."""
    pass # нужно только имя


# 2. СХЕМЫ ДЛЯ КОМПЛЕКТОВ ЕГЭ (ExamSets)
class ExamSetBase(BaseModel):
    """Базовая схема для комплекта ЕГЭ."""
    name: str

class ExamSetOut(ExamSetBase):
    """Схема для вывода комплекта ЕГЭ с предметами."""
    id: int
    subjects: List[SubjectOut]
    
    model_config = ConfigDict(from_attributes=True)

class ExamSetCreate(ExamSetBase):
    """Схема для создания нового комплекта ЕГЭ."""
    subject_ids: List[int]


# 3. СХЕМЫ ДЛЯ СТАТИСТИКИ ПО ЗАЯВЛЕНИЯМ (ApplicationStats)
class ApplicationStatsBase(BaseModel):
    """Базовая схема для статистики по заявлениям."""
    id: int
    specialty_id: int
    year: int
    applications: int | None = None
    kcp: int | None = None
    enrolled: int | None = None

class ApplicationStatsOut(ApplicationStatsBase):
    """Схема для вывода статистики по заявлениям."""
    id: int
    specialty_id: int
    
    model_config = ConfigDict(from_attributes=True)

class ApplicationStatsCreate(ApplicationStatsBase):
    """Схема для создания новой статистики по заявлениям."""
    specialty_id: int


# 4. СХЕМЫ ДЛЯ СТАТИСТИКИ ПО ЭКЗАМЕНАМ (ExamStats)
class ExamStatsBase(BaseModel):
    """Базовая схема для статистики по экзаменам."""
    year: int
    participants: int

class ExamStatsOut(ExamStatsBase):
    """Схема для вывода статистики по экзаменам."""
    id: int
    subject_id: int
    
    model_config = ConfigDict(from_attributes=True)

class ExamStatsCreate(ExamStatsBase):
    """Схема для создания новой статистики по экзаменам."""
    subject_id: int


# 5. СХЕМЫ ДЛЯ СТАТИСТИКИ ПО РОЖДЕНИЯМ (BirthRate)
class BirthRateBase(BaseModel):
    year: int
    births: int

class BirthRateOut(BirthRateBase):
    model_config = ConfigDict(from_attributes=True)

class BirthRateCreate(BirthRateBase):
    pass


# 6. СХЕМЫ ДЛЯ СПЕЦИАЛЬНОСТЕЙ (Specialties)
class SpecialtyBase(BaseModel):
    """Базовая схема для специальности."""
    code: str | None = None
    name: str

    @field_validator("code", mode="before")
    @classmethod
    def clean_nan(cls, c):
        if isinstance(c, str) and c.lower() == "nan":
            return None
        return c

class SpecialtyShortOut(SpecialtyBase):
    """Схема для вывода специальности (краткая)."""
    id: int

    model_config = ConfigDict(from_attributes=True)

class SpecialtyOut(SpecialtyBase):
    """Схема для вывода специальности с комплектами и заявлениями по годам."""
    id: int
    exam_sets: List[ExamSetOut]
    application_stats: List[ApplicationStatsOut]
    
    model_config = ConfigDict(from_attributes=True)
    

class SpecialtyCreate(SpecialtyBase):
    """Схема для создания новой специальности."""
    exam_set_ids: List[int] # IDs комплектов ЕГЭ

class SpecialtyUpdate(BaseModel):
    """Схема для обновления специальности."""
    code: Optional[str] = None
    name: Optional[str] = None
    exam_set_ids: Optional[List[int]] = None

# СХЕМЫ ДЛЯ ОТЧЁТОВ
class ReportCreate(BaseModel):
    input_specialty: str
    history_range: Tuple[int, int]
    forecast_range: Tuple[int, int]
    method: str

class ReportCreateOut(BaseModel):
    success: bool
    report_url: HttpUrl

class ReportOut(BaseModel):
    id: int
    specialty_id: int
    specialty_full_name: str
    method: str
    start_year: int
    current_year: int
    end_year: int
    url: HttpUrl