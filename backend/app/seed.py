import pandas as pd
import numpy as np
from app.models import Subject, ExamSet, Specialty, ApplicationStats, BirthRate, ExamStats, ExamSetItem, SpecialtyExamSet
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple, List

# СЛОВАРИ ВИДА "НАЗВАНИЕ: ОБЪЕКТ" (для быстрого доступа к объектам)
specialties = {} # name: Specialty
subjects = {} # name: Subject
exam_sets = {} # name: ExamSet
spec_sets = {} # specialty_name: [ExamSet]
applications = {} # (specialty_name, year): ApplicationStats

def _get_dfs() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Возвращает кортеж датафреймов."""
     # специальности
    df_spec = pd.read_excel('data/excel/application_stats.xlsx', sheet_name='Направления', dtype=str)

    # заявления (а также предметы и комплекты)
    df_apps = pd.read_excel('data/excel/application_stats.xlsx', sheet_name='Заявления', header=[0, 1])
    df_apps = _transform_columns(df_apps)
    df_apps = _transform_rows(df_apps)

    # рождаемость (взято из https://rosstat.gov.ru/bgd/regl/B21_16/Main.htm)
    df_births = pd.read_excel('data/excel/birth_stats.xlsx')

    # статистика по экзаменам (данные взяты из документа Word)
    df_exams = pd.read_excel('data/excel/exam_stats.xlsx')

    return df_spec, df_apps, df_births, df_exams

async def seed(session: AsyncSession) -> None:
    """Заполняет базу данных (Excel + показатели)."""
    df_spec, df_apps, df_births, df_exams = _get_dfs()

    # заполняем из Excel-файлов
    await _fill_specialties(df_spec, session)
    await _fill_subjects_sets_apps(df_apps, session)
    await _fill_births(df_births, session)
    await _fill_exams(df_exams, session)

def _transform_columns(df) -> pd.DataFrame:
    """Убирает NaN и Unnamed из заголовков (1 и 2 строки в Excel)."""
    new_columns = []
    current_year = None

    for col in df.columns:
        year_level = col[0]
        column_name = col[1]
        
        # если первый уровень не Unnamed, значит это новый год
        if "Unnamed" not in str(year_level):
            current_year = year_level
        
        new_columns.append((current_year, column_name))

    # столбцы в Pandas - строки 1 и 2 в Excel
    df.columns = pd.MultiIndex.from_tuples(new_columns)
    return df

def _transform_rows(df) -> pd.DataFrame:
    """Убирает NaN из строк и убирает полностью пустые строки."""
    df = df.dropna(axis=0, how='all') # удаляем полностью пустые строки
    df.iloc[:, 0] = df.iloc[:, 0].ffill() # протягиваем номер комплекта ЕГЭ
    df.iloc[:, 1] = df.iloc[:, 1].ffill() # протягиваем сам комплект ЕГЭ
    df.iloc[:, 2] = df.iloc[:, 2].ffill() # протягиваем направление
    return df

async def _fill_specialties(df, session: AsyncSession):
    for _, row in df.iterrows():
        code = str(row['Код'])
        name = str(row['Направление'])

        spec = Specialty(code=code, name=name)
        specialties[name] = spec
        session.add(spec)
        await session.flush()

    await session.commit()

async def _fill_subjects_sets_apps(df, session: AsyncSession):
    """Заполняет предметы, комплекты ЕГЭ и статистику по заявлениям."""
    for _, row in df.iterrows():
        # добавляем предметы
        subject_names, cur_subjects = await __fill_subjects(df, row, session)
        # добавляем комплекты
        spec_name = await __fill_exam_sets(df, row, subject_names, cur_subjects, session)
        # добавляем статистику по заявлениям
        await __fill_apps(df, row, spec_name, session)
        
    # добавляем связи "Направление - Комплект ЕГЭ"
    for name in spec_sets:
        spec = specialties[name]
        for exam_set in spec_sets[name]:
            association_spec_set = SpecialtyExamSet(specialty_id=spec.id, set_id=exam_set.id)
            session.add(association_spec_set)
            await session.flush()
    
    await session.commit()

async def __fill_subjects(df, row, session: AsyncSession) -> Tuple[List[str], List[Subject]]:
    """Заполняет базу данных предметами и возвращает вспомогательные данные."""
    subjects_raw = row[df.columns[1]]

    # список названий в виде строк
    subject_names = [s.strip() for s in str(subjects_raw).split('\n') if s.strip()]

    # список объектов предметов
    cur_subjects = []

    for name in subject_names:
        if name not in subjects:
            subj = Subject(name=name)
            subjects[name] = subj
            session.add(subj)
            await session.flush()
        cur_subjects.append(subjects[name])
    
    return subject_names, cur_subjects

async def __fill_exam_sets(df, row, subject_names, cur_subjects, session: AsyncSession) -> str:
    """Заполняет комплекты ЕГЭ, связи между комплектами и предметами и возвращает название направления."""
    # название комплекта в виде строки
    set_name = ", ".join(subject_names)
    # название направления
    spec_name = str(row[df.columns[2]]).strip()

    if set_name not in exam_sets:
        set_obj = ExamSet(name=set_name)            
        exam_sets[set_name] = set_obj
        session.add(set_obj)
        await session.flush()

        for subj in cur_subjects:
            association_item = ExamSetItem(set_id=set_obj.id, subject_id=subj.id)
            session.add(association_item)
    
    # добавляем комплект к направлению
    spec_sets.setdefault(spec_name, []).append(exam_sets[set_name])

    return spec_name

async def __fill_apps(df, row, spec_name, session: AsyncSession):
    """Заполняет статистику по заявлениям."""
    # собираем статистику по годам (на каждый год 3 столбца)
    for col_idx in range(3, len(df.columns), 3):
        # год - первое значение в заголовке
        year = int(df.columns[col_idx][0])

        # избегаем дубликатов
        if (spec_name, year) in applications:
            continue

        # считываем значения столбцов (кол-во заявок, КЦП, кол-во зачисленных)
        apps = None if pd.isna(row[df.columns[col_idx + 1]]) else row[df.columns[col_idx + 1]]
        kcp = None if pd.isna(row[df.columns[col_idx]]) else row[df.columns[col_idx]]
        enrolled = None if pd.isna(row[df.columns[col_idx + 2]]) else row[df.columns[col_idx + 2]]
        
        stats = ApplicationStats(specialty=specialties[spec_name],
                                 year=year,
                                 applications=apps,
                                 kcp=kcp,
                                 enrolled=enrolled)
        
        applications[(spec_name, year)] = stats
        session.add(stats)
        await session.flush()

async def _fill_births(df, session: AsyncSession):
    for _, row in df.iterrows():
        year = int(row['Год'])
        births = int(row['Количество рожденных'])
        birth_stats = BirthRate(year=year, births=births)
        session.add(birth_stats)
        await session.flush()

    await session.commit()

async def _fill_exams(df, session: AsyncSession):
    for _, row in df.iterrows():
        subj_name = row['Предмет']
        subject = subjects[subj_name]
        for col_idx in range(1, len(df.columns)):
            year = df.columns[col_idx]
            participants = row[year]
            stats = ExamStats(subject=subject, year=int(year), participants=int(participants))
            session.add(stats)
            await session.flush()

    await session.commit()