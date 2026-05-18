import asyncio
import pandas as pd
import numpy as np
from sqlalchemy import text
from app.database import engine
from typing import Dict

async def fetch_query_to_df(async_engine, query_str):
    async with async_engine.connect() as conn:
        result = await conn.execute(text(query_str))
        rows = result.fetchall()
        columns = result.keys()
        df = pd.DataFrame(rows, columns=columns)
    return df

def history_demand(df: pd.DataFrame, weights: Dict[str, float] | None) -> pd.DataFrame:
    """Считает востребованность специальности по историческим данным.

    D_final = (w1 * X1 + w2 * X2 + w3 * X3 + w4 * X4) * exp(w5 * X5), где
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
        pd.Series: Вектор с прогнозами для каждого объекта (специальности)
    """
    if weights is None:
        weights = {"w1": 0.25, "w2": 0.25, "w3": 0.4, "w4": 0.1, "w5": -10}

    # сортируем для дальнейшей группировки
    df = df.sort_values(by=["specialty_id", "year"]).reset_index(drop=True)

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
    df["D2"] = 0.2 * df["apps_diff"] + 0.2 * df["apps_growth"] + 0.4 * df["apps_diff"] * df["apps_growth"]

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

    # СЧИТАЕМ ГОДОВОЙ ПОКАЗАТЕЛЬ D_year
    df["D_year"] = (weights["w1"] * df["D1"] + 
                    weights["w2"] * df["D2"] + 
                    weights["w3"] * df["D3"] + 
                    weights["w4"] * df["D4"] *
                    df["P"])

    # СЧИТАЕМ ИТОГОВЫЙ ПОКАЗАТЕЛЬ D ДЛЯ ВСЕХ СПЕЦИАЛЬНОСТЕЙ
    demand = df.groupby("specialty_id")["D_year"].mean().reset_index(name='D')

    return demand

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

async def main(weights=None):
    df = await fetch_query_to_df(engine, "SELECT * FROM application_stats")
    df = df.dropna()

    demand = history_demand(df, weights)
    print(demand)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())