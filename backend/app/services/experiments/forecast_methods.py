import pandas as pd
import numpy as np
from app.database import fetch_query_to_df
import asyncio

START_YEAR = 2019
END_YEAR = 2023

async def test_forecast_methods():
    """Тестирует функции прогнозирования и возвращает ошибку wMAPE (взвешенная средняя ошибка в процентах)."""
    for forecast_year in range(START_YEAR + 1, END_YEAR + 1):
        print(f"Год прогноза: {forecast_year}")
        query = """
            SELECT a.*
            FROM public.application_stats AS a
            JOIN public.specialties AS s ON a.specialty_id = s.id
            WHERE a.year BETWEEN :start_year AND :forecast_year
            ORDER BY a.specialty_id, a.year ASC;
        """
        df = await fetch_query_to_df(
            query,
            params={"start_year": START_YEAR, "forecast_year": forecast_year}
        )
        df = df.dropna() # убираем строки хотя бы с одним пропуском

        functions_list = [
            forecast_enrolled_with_plan_completion_rate_rate,
            forecast_applications_with_exam_participants,
        ]
        for func in functions_list:
            wmape = await func(df, forecast_year)
            print(f"Функция {func.__name__}: wMAPE = {round(wmape, 1)}%")


async def forecast_enrolled_with_plan_completion_rate_rate(df, forecast_year) -> float:
    """Прогнозирует зачисленных через выполняемость плана по набору.
    
    Формула: Зачисленные_i = 1/n * sum(Зачисленные_j / kcp_j) * kcp_i, где:
        * j - год в диапазоне исторических данных (до i)
        * i - прогнозируемый год
        * 1/n * sum(Зачисленные_j / kcp_j) - средняя выполняемость плана по набору на истории
        * kcp_i - КЦП по специальности в прогнозируемом году (считаем, что уже известно, т.к. данные приходят в январе, а набор - в августе)
    """
    history_df = df[df["year"] < forecast_year].copy().sort_values(["specialty_id", "year"]).reset_index(drop=True)
    # мы знаем КЦП, но не знаем заявления в прогнозируемом году, зачисленные только как ориентир для сравнения с прогнозом
    expected_df = (
        df[df["year"] == forecast_year][["id", "specialty_id", "year", "kcp", "enrolled"]]
        .copy()
        .sort_values(["specialty_id", "year"]).reset_index(drop=True)
    )
    expected_df.rename(columns={"enrolled": "enrolled_exp"}, inplace=True)

    history_df["plan_completion_rate"] = np.where(history_df["kcp"] == 0, np.nan, history_df["enrolled"] / history_df["kcp"])
    stats = history_df.groupby("specialty_id", as_index=False)["plan_completion_rate"].last()
    stats.rename(columns={"plan_completion_rate": "median_plan_completion"}, inplace=True)

    total = pd.merge(stats, expected_df, how="left", on="specialty_id")
    total["enrolled_pred"] = total["kcp"] * total["median_plan_completion"]
    total["diff"] = (total["enrolled_exp"] - total["enrolled_pred"]).abs()
    total.dropna(inplace=True)
    wmape = round(total["diff"].sum() / total["enrolled_exp"].sum() * 100, 1)

    return wmape

async def forecast_applications_with_exam_participants(df, forecast_year) -> float:
    """Прогнозирует количество заявлений через количество участников экзамена.
    
    Формула: Заявления_i = 1/n * sum(Заявления_j / exam_participants_j) * exam_participants_i, где:
        * j - год в диапазоне исторических данных (до i)
        * i - прогнозируемый год
        * 1/n * sum(Заявления_j / exam_participants_j) - средняя конверсия участников экзамена в заявления на истории
        * exam_participants_i - количество участников экзаменов по специальности в прогнозируемом году (считаем, что уже известно, т.к. экзамены в июне, а набор - в августе)
    
    Важно: участники экзамена считаются как сумма всех участников ЕГЭ по предметам, по которым можно поступить на специальность.
    """
    query = """
        SELECT cte.*, a.applications FROM (
            SELECT specialty_id, year, sum(participants) AS participants FROM (
                SELECT DISTINCT ses.specialty_id, stats.year, stats.participants 
                FROM public.specialty_exam_sets AS ses
                JOIN public.exam_sets AS es ON ses.set_id = es.id
                JOIN public.exam_set_items AS esi ON es.id = esi.set_id
                JOIN public.exam_stats AS stats ON esi.subject_id = stats.subject_id
                ORDER BY ses.specialty_id, stats.year ASC
            )
            GROUP BY specialty_id, year
            ORDER BY specialty_id, year ASC
        ) as cte -- общее количество сдававших ЕГЭ по предметам, которые нужны при поступлении на данную специальность
        JOIN public.application_stats AS a ON a.specialty_id = cte.specialty_id AND a.year = cte.year
        ORDER BY cte.specialty_id, cte.year ASC;
    """

    df = await fetch_query_to_df(query)
    df["conversions"] = df["applications"] / df["participants"]
    stats = df[(df["year"] < forecast_year)].groupby("specialty_id").median()[["applications", "conversions"]].reset_index()
    new_data = df[df["year"] == forecast_year].copy()[["specialty_id", "applications", "participants"]]
    total = pd.merge(stats, new_data, how="inner", on="specialty_id")
    total["apps_pred"] = total["conversions"] * total["participants"]
    total["diff"] = (total["applications_y"] - total["apps_pred"]).abs()
    wmape = total["diff"].sum() / total["applications_y"].sum() * 100

    return wmape


if __name__ == "__main__":
    asyncio.run(test_forecast_methods())
