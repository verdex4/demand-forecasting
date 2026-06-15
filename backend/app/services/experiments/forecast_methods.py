import pandas as pd
import numpy as np
from app.database import fetch_query_to_df
import asyncio
from collections import defaultdict

START_YEAR = 2019
END_YEAR = 2023

async def test_forecast_methods():
    """Тестирует функции прогнозирования и возвращает ошибку wMAPE (взвешенная средняя ошибка в процентах)."""
    methods = defaultdict(float)
    functions_list = [
        forecast_enrolled_with_plan_completion_rate,
        forecast_applications_with_exam_participants,
    ]
    grouping_methods = ["mean", "median", "last"]
    
    for forecast_year in range(START_YEAR + 1, END_YEAR + 1):
        print(f"Год прогноза: {forecast_year}")
        query = """
            SELECT a.*
            FROM public.application_stats AS a
            WHERE a.year BETWEEN :start_year AND :forecast_year
            ORDER BY a.specialty_id, a.year ASC;
        """
        df = await fetch_query_to_df(
            query,
            params={"start_year": START_YEAR, "forecast_year": forecast_year}
        )

        for func in functions_list:
            for grouping_method in grouping_methods:
                wmape = await func(df, forecast_year, grouping_method)
                methods[(func.__name__, grouping_method)] += wmape
                print(f"Функция {func.__name__}: Метод группировки = {grouping_method}, wMAPE = {round(wmape, 1)}%")
    
    print()
    for func in functions_list:
        best_method, best_sum_wmape = "", float("inf")
        for method in grouping_methods:
            sum_wmape = methods[(func.__name__, method)]
            if sum_wmape < best_sum_wmape:
                best_method, best_sum_wmape = method, sum_wmape
        
        avg_wmape = best_sum_wmape / (END_YEAR - START_YEAR)
        print(f"Функция {func.__name__}: Лучший метод группировки = {best_method}, средний wMAPE = {round(avg_wmape, 1)}%")


async def forecast_enrolled_with_plan_completion_rate(df, forecast_year, grouping_method) -> float:
    """Прогнозирует зачисленных через выполняемость плана по набору.
    
    Формула: Зачисленные_i = func(Зачисленные_j / kcp_j) * kcp_i, где:
        * j - год в диапазоне исторических данных (до i)
        * i - прогнозируемый год
        * Зачисленные_j / kcp_j - выполняемость плана по набору в j-том году
        * func - группирующая функция (например, среднее, медиана или последнее значение)
        * kcp_i - КЦП по специальности в прогнозируемом году (считаем, что уже известно, т.к. данные приходят в январе, а набор - в августе)
    """
    history_df = df[df["year"] < forecast_year].sort_values(["specialty_id", "year"]).reset_index(drop=True)
    # мы знаем КЦП, но не знаем заявления в прогнозируемом году, зачисленные только как ориентир для сравнения с прогнозом
    expected_df = (
        df.loc[df["year"] == forecast_year, ["id", "specialty_id", "year", "kcp", "enrolled"]]
        .sort_values(["specialty_id", "year"]).reset_index(drop=True)
    )
    expected_df.rename(columns={"enrolled": "enrolled_exp"}, inplace=True)
    history_df["plan_completion_rate"] = np.where(history_df["kcp"] == 0, np.nan, history_df["enrolled"] / history_df["kcp"])

    if grouping_method == "mean":
        stats = history_df.groupby("specialty_id", as_index=False)["plan_completion_rate"].mean()
    elif grouping_method == "median":
        stats = history_df.groupby("specialty_id", as_index=False)["plan_completion_rate"].median()
    elif grouping_method == "last":
        stats = history_df.groupby("specialty_id", as_index=False)["plan_completion_rate"].last()
    else:
        raise ValueError(f"Неизвестный grouping_method: {grouping_method}")

    total = pd.merge(stats, expected_df, how="left", on="specialty_id")
    total["enrolled_pred"] = total["kcp"] * total["plan_completion_rate"]
    total["diff"] = (total["enrolled_exp"] - total["enrolled_pred"]).abs()
    
    wmape = total["diff"].sum() / total["enrolled_exp"].sum() * 100
    return wmape

async def forecast_applications_with_exam_participants(df, forecast_year, grouping_method) -> float:
    """Прогнозирует количество заявлений через количество участников экзамена.
    
    Формула: Заявления_i = func(Заявления_j / exam_participants_j) * exam_participants_i, где:
        * j - год в диапазоне исторических данных (до i)
        * i - прогнозируемый год
        * Заявления_j / exam_participants_j - конверсия участников экзамена в заявления в j-том году
        * func - группирующая функция (например, среднее, медиана или последнее значение)
        * exam_participants_i - количество участников экзаменов по специальности в прогнозируемом году (считаем, что уже известно, т.к. экзамены в июне, а набор - в августе)
    
    Важно: участники экзамена считаются как сумма всех участников ЕГЭ по предметам, по которым можно поступить на специальность.
    """
    query = """
        SELECT 
            cte.specialty_id, 
            cte.year, 
            cte.participants,
            a.applications
        FROM (
            SELECT 
                specialty_id, 
                year, 
                SUM(participants) AS participants
            FROM (
                SELECT DISTINCT 
                    ses.specialty_id, 
                    stats.year, 
                    stats.subject_id,
                    stats.participants
                FROM public.specialty_exam_sets AS ses
                JOIN public.exam_sets AS es ON ses.set_id = es.id
                JOIN public.exam_set_items AS esi ON es.id = esi.set_id
                JOIN public.exam_stats AS stats ON esi.subject_id = stats.subject_id
                WHERE stats.year BETWEEN :start_year AND :forecast_year
            ) AS unique_subjects
            GROUP BY specialty_id, year
        ) AS cte
        JOIN public.application_stats AS a 
          ON a.specialty_id = cte.specialty_id 
         AND a.year = cte.year
        ORDER BY cte.specialty_id, cte.year ASC;
    """

    df = await fetch_query_to_df(query, params={"start_year": START_YEAR, "forecast_year": forecast_year})
    history_df = df[df["year"] < forecast_year].sort_values(["specialty_id", "year"]).reset_index(drop=True)
    expected_df = (
        df.loc[df["year"] == forecast_year, ["specialty_id", "year", "participants", "applications"]]
        .sort_values(["specialty_id", "year"]).reset_index(drop=True)
    )
    expected_df = expected_df.rename(columns={"applications": "applications_exp"})

    history_df["conversion"] = history_df["applications"] / history_df["participants"]

    if grouping_method == "mean":
        stats = history_df.groupby("specialty_id").mean()["conversion"].reset_index()
    elif grouping_method == "median":
        stats = history_df.groupby("specialty_id").median()["conversion"].reset_index()
    elif grouping_method == "last":
        stats = history_df.groupby("specialty_id").last()["conversion"].reset_index()
    else:
        raise ValueError(f"Неизвестный grouping_method: {grouping_method}")
    
    total = pd.merge(stats, expected_df, how="inner", on="specialty_id")
    total["applications_pred"] = total["conversion"] * total["participants"]
    total["diff"] = (total["applications_exp"] - total["applications_pred"]).abs()
    wmape = total["diff"].sum() / total["applications_exp"].sum() * 100

    return wmape


if __name__ == "__main__":
    asyncio.run(test_forecast_methods())
