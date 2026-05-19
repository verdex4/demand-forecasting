import asyncio
import pandas as pd
import numpy as np
from sqlalchemy import text
from app.database import engine
from typing import Dict, Tuple, List

async def make_forecast(specialties_names: List[str],
                        method: str,
                        history_range: Tuple[int, int],
                        forecast_range: Tuple[int, int],
                        weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Прогнозирует востребованность специальностей с помощью указанного метода.

    Доступные методы:
    * SMA_x - скользящее среднее за x лет

    Args:
        specialties_names (str): Названия специальностей
        method (str): Метод прогнозирования
        history_range (Tuple[int, int]): Диапазон исторических данных
        forecast_range (Tuple[int, int]): Диапазон прогнозирования
        weights (Dict[str, float] | None): Веса модели

    Returns:
        pd.DataFrame: Датафрейм с прогнозными данными
    """
    # получаем данные
    query = """
        SELECT a.*
        FROM public.application_stats AS a
        JOIN public.specialties AS s ON a.specialty_id = s.id
        WHERE a.year BETWEEN :start_year AND :end_year
        AND s.name = ANY(:specialties_names)
        ORDER BY a.specialty_id, a.year ASC;
    """
    df = await _fetch_query_to_df(
        engine, 
        query,
        params={"start_year": history_range[0], 
                "end_year": history_range[1],
                "specialties_names": specialties_names}
    )
    await engine.dispose()

    df = df.dropna() # убираем строки хотя бы с одним пропуском

    # выбираем нужную функцию для прогнозирования
    method = method.lower()
    params = {}
    _forecast_func = None
    if method.startswith("sma_"):
        params["sma_window"] = int(method[4:])
        _forecast_func = _forecast_sma

    if _forecast_func is None:
        raise ValueError(f"Метода прогнозирования {method} не существует, смотри доступные методы в описании к функции.")

    # прогнозируем ключевые показатели: кол-во заявлений, КЦП, кол-во зачисленных
    df = _forecast_func(df, forecast_range, **params)

    # считаем показатели востребованности
    df = _calc_demand(df, weights)

    cols = ["specialty_id", "year", "applications", "kcp", "enrolled", "D1", "D2", "D3", "D4", "D"]
    df = df[cols].sort_values(["specialty_id", "year"])
    print(df)

    return df

async def _fetch_query_to_df(async_engine, query_str, params=None):
    async with async_engine.connect() as conn:
        result = await conn.execute(text(query_str), params or {})
        rows = result.fetchall()
        columns = result.keys()
        df = pd.DataFrame(rows, columns=columns)
    return df

def _calc_demand(df: pd.DataFrame, weights: Dict[str, float] | None = None) -> pd.DataFrame:
    """Считает показатели востребованности специальности.

    D = (w1 * X1 + w2 * X2 + w3 * X3 + w4 * X4) * exp(w5 * X5), где
    * X1 - коммерческий интерес
    * X2 - показатель заявлений (доля рынка + рост)
    * X3 - показатель конкурса (доля рынка + рост)
    * X4 - показатель КЦП (доля рынка + рост)
    * X5 - доля недобора относительно КЦП

    Свойства:
    * X_i - вектора
    * 0 <= x <= 1 для любого x в (X1, X2, X3, X4, X5)
    * w1 + w2 + w3 + w4 = 1; w5 < 0, чем меньше, тем жестче штраф

    Значения по умолчанию:
    * w1 = 0.25
    * w2 = 0.25
    * w3 = 0.4
    * w4 = 0.1
    * w5 = -10

    Args:
        df (pd.DataFrame): Датафрейм с данными.
        coeffs (dict): Коэффициенты прогноза. Пример: {"k1": 0.25, "k2": 0.4, "k3": 0.25, "k4": 0.1, "k5": -10, "k6": -2}.

    Returns:
        pd.DataFrame: Датафрейм с показателями востребованности.
    """
    if weights is None:
        weights = {"w1": 0.25, "w2": 0.25, "w3": 0.4, "w4": 0.1, "w5": -10}

    # ДОБАВЛЯЕМ D1 - коммерческий интерес
    # если зачисленных нет или их меньше, чем КЦП, то D1 = 0, иначе считаем по формуле
    df["D1"] = np.where((df["enrolled"] == 0) | (df["enrolled"] < df["kcp"]), 
                        0, 
                        (df["enrolled"] - df["kcp"]) / df["enrolled"])

    # ДОБАВЛЯЕМ D2 - количество заявлений
    # вычисляем разницу с медианой
    median_apps = df["applications"].median()
    df["apps_diff"] = _normalize_diff(df["applications"], median_apps)

    # вычисляем прирост заявлений
    df["apps_growth"] = _smape_normalized_diff(df, "applications")

    # считаем D2 как взвешенную сумму x1, x2 и синергии x1, x2 (если x1, x2 высокие, то D2 высокий)
    df["D2"] = 0.3 * df["apps_diff"] + 0.3 * df["apps_growth"] + 0.4 * df["apps_diff"] * df["apps_growth"]

    # ДОБАВЛЯЕМ D3 - конкурс (количество человек на место)
    # считаем кол-во человек на место
    df["competition"] = np.where(
        df["kcp"] == 0, # если КЦП = 0, то считаем конкурс по другой формуле, иначе по обычной
        np.where(df["enrolled"] == 0, 0, df["applications"] / df["enrolled"]), 
        df["applications"] / df["kcp"]
    )

    # вычисляем прирост конкурса
    df["competition_growth"] = _smape_normalized_diff(df, "competition")

    # вычисляем разницу с медианным конкурсом
    median_competition = df["competition"].median()
    df["competition_diff"] = _normalize_diff(df["competition"], median_competition)

    # вес 0.7 для разницы с медианой и 0.3 для роста
    df["D3"] = 0.7 * df["competition_diff"] + 0.3 * df["competition_growth"]

    # удаляем лишнее
    df.drop(["competition", "competition_growth"], axis=1, inplace=True)

    # ДОБАВЛЯЕМ D4 - прирост КЦП по sMAPE
    # вычисляем разницу с медианой
    median_kcp = df["kcp"].median()
    df["kcp_diff"] = _normalize_diff(df["kcp"], median_kcp)

    # вычисляем прирост заявлений
    df["kcp_growth"] = _smape_normalized_diff(df, "kcp")

    # считаем D4 как взвешенную сумму
    df["D4"] = 0.4 * df["kcp_diff"] + 0.6 * df["kcp_growth"]

    # ДОБАВЛЯЕМ ШТРАФ P
    # обрабатываем крайние случаи
    conditions = [
        df["enrolled"] == 0,         # нет зачисленных
        df["enrolled"] >= df["kcp"], # заполнили все бюджетные места
    ]

    # выбираем соответствующие значения
    choices = [
        0, # полный штраф за отсутствие зачисленных
        1  # штрафа нет
    ]

    # ставим соотвествующие значения, если условия не подошли - считаем по формуле
    df["P"] = np.select(conditions, 
                        choices,
                        default=np.exp(weights["w5"] * (df["kcp"] - df["enrolled"]) / df["kcp"]))

    # СЧИТАЕМ ГОДОВОЙ ПОКАЗАТЕЛЬ D
    df["D"] = (weights["w1"] * df["D1"] + 
                    weights["w2"] * df["D2"] + 
                    weights["w3"] * df["D3"] + 
                    weights["w4"] * df["D4"] *
                    df["P"])

    return df

def _smape_normalized_diff(df, col: str, k=-2) -> np.ndarray:
    """Вычисление нормализованного изменения роста по sMAPE от 0 до 1.

    Вычисление прироста по sMAPE:
    * x = -2 -> sMAPE = 0
    * x = 0 -> sMAPE = 0.5
    * x = 2 -> sMAPE = 1

    Нормализация:
    * sMAPE = -2 -> result = 0
    * sMAPE = 0 -> result = 0.5
    * sMAPE = 2 -> result = 1

    Метод sMAPE позволяет вычислить прирост какого-либо количества и сжать его в диапазон [-2, 2].
    Полученное значение нормализуется в диапазон [0, 1] и отображает силу роста.

    Зачем: при обычном приросте в процентах может получиться случай, когда происходит изменение
    с 0 до 30, это выдаст бесконечность. Метод sMAPE позволяет сжать значения в диапазон [-2, 2].
    То есть даже если в процентах бесконечность, sMAPE покажет 2.

    Нормализация через сигмоиду приводит результат в диапазон [0, 1] и делает S-образный график, 
    быстрее устремляя значения в 0 и в 1, чем обычная линейная функция.

    Args:
        df: DataFrame
        col: название столбца, по которому нужно считать разницу

    Returns:
        np.ndarray
    
    Notes:
        Не изменяет исходный DataFrame
    """
    df = df.copy()
    prev = "prev_value"

    # добавляем значение предыдущего столбца (группируя по специальностям)
    df[prev] = df.groupby("specialty_id")[col].transform(lambda x: x.shift(1))
    
    # числитель и знаменатель для вычисления среднего роста по sMAPE
    numerator = df[col] - df[prev]
    denominator = (df[col] + df[prev]) / 2

    # обрабатываем крайние случаи
    conditions = [
        df[prev].isna(),               # первая строка (не можем вычислить предыдущее)
        (df[col] == 0) & (df[prev] == 0) # оба значения нулевые
    ]

    # выбираем соответствующие значения
    choices = [
        np.nan,
        0.0
    ]

    # ставим соотвествующие значения, если условия не подошли - считаем по формуле
    values = np.select(conditions, choices, default=numerator / denominator)

    # нормализуем через сигмоиду
    values = 1 / (1 + np.exp(k * values))

    return values

def _normalize_diff(x: pd.Series, mean, k=2) -> np.ndarray:
    """Нормализация разницы со средним в диапазон [0, 1].

    Нормализация:
    * x = 0 -> result = 0
    * x = mean -> result = 0.5
    * x = inf -> result = 1

    Args:
        x: столбец, по которому нужно считать разницу
        mean: значение, с которым считаем разницу (среднее)
        k: коэффициент изгиба. Чем больше, тем больше изгиб и быстрее стремление к 0 или 1.

    Returns:
        np.ndarray
    """
    # возведение в степень прижимает значение к 0 до среднего и к 1 после среднего
    return np.where(x == 0, 
                    0, 
                    x**k / (x**k + mean**k))

def _forecast_sma(df: pd.DataFrame, forecast_range: Tuple[int, int], sma_window: int) -> pd.DataFrame:
    """Прогнозирует ключевые показатели с помощью взятия среднего из истории."""
    if df[df["year"] == forecast_range[0] - sma_window].empty:
        raise IndexError(f"Введено слишком большое значение sma_window.")
    
    indicators = ["applications", "kcp", "enrolled"]

    for year in range(forecast_range[0], forecast_range[1] + 1):
        window_data = df[df["year"].between(year - sma_window, year - 1)]
        cur_forecast = window_data.groupby("specialty_id", as_index=False)[indicators].mean()
        cur_forecast[indicators] = np.ceil(cur_forecast[indicators]).astype(int)
        cur_forecast["year"] = year
        df = pd.concat([df, cur_forecast], ignore_index=True)

    return df

if __name__ == "__main__":
    asyncio.run(make_forecast(["Астрономия", "Прикладная информатика"], "sma_3", (2019, 2023), (2024, 2026)))