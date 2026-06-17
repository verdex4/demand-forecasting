import pandas as pd
import numpy as np
from app.database import fetch_query_to_df, fetch_query_to_scalar
from app.services.utils import raise_error

async def make_forecast(
    specialty: str,
    method: str,
    history_range: tuple[int, int],
    forecast_range: tuple[int, int],
    kcp_manual: dict[str, int] | None = None,
    kcp_growth_pct: float | None = None,
    paid_manual: dict[str, int] | None = None,
    paid_growth_pct: float | None = None,
    weights: dict[str, float] | None = None
) -> tuple[pd.DataFrame, dict]:
    """Прогнозирует спрос (заявления) с помощью указанного метода и считает востребованность специальностей.

    Args:
        method (str): Название метода прогнозирования
        history_range (Tuple[int, int]): Диапазон исторических данных
        forecast_range (Tuple[int, int]): Диапазон прогнозирования
        weights (Dict[str, float] | None): Веса модели

    Returns:
        pd.DataFrame: Датафрейм с прогнозными данными
    """
    # считываем данные о заявлениях
    query = """
        SELECT 
            a.specialty_id,
            a.year,
            a.applications,
            a.kcp,
            a.enrolled
        FROM public.application_stats AS a
        WHERE a.year BETWEEN :start_year AND :end_year
        ORDER BY a.specialty_id, a.year ASC;
    """
    df = await fetch_query_to_df(
        query,
        params={"start_year": history_range[0], "end_year": history_range[1]}
    )

    # удаляем записи, где набор не вёлся (это ухудшает прогноз)
    inactive_rows = (df['kcp'] == 0) & (df['enrolled'] == 0)
    df.loc[inactive_rows, ['applications', 'kcp', 'enrolled']] = pd.NA
    # удаляем и те, у которых нет части данных, т.к. не хватит данных для подсчёта
    df = df.dropna().reset_index(drop=True).astype("Int64")

    # проверяем корректность ввода метода
    method_in_db = await fetch_query_to_scalar(
        "SELECT name FROM public.forecast_methods WHERE name = :name",
        params={"name": method}
    )
    if not method_in_db:
        available = await fetch_query_to_df("SELECT slug FROM public.forecast_methods")
        raise_error(f"Метода прогнозирования {method} не существует, доступные: {', '.join(available['slug'].values)}")

    # определяем функцию прогнозирования
    params = {}
    _forecast_func = None
    if method.lower() == "последнее значение":
        _forecast_func = _forecast_last
    if method.lower().startswith("скользящее среднее за"):
        params["sma_window"] = int(method.split(" ")[-2])
        _forecast_func = _forecast_sma
    if method.lower() == "демографический метод":
        _forecast_func = _forecast_demographic
    if method.lower() == "экспоненциальное сглаживание":
        _forecast_func = _forecast_exp_smoothing
    
    if not _forecast_func:
        raise_error("Internal error: функция прогнозирования не найдена", status_code=500)
    
    # прогнозируем спрос: количество заявлений по всем специальностям
    df = await _forecast_func(df, history_range, forecast_range, **params)
    # HACK: костыль для тестирования. Надо разделить логику: прогноз и подсчёт показателей
    if specialty == "all":
        return df, {}

    specialty_id = await fetch_query_to_scalar(
        "SELECT id FROM public.specialties WHERE code = :code",
        params={"code": specialty.split(" ")[0]}
    )
    df_spec = df[df["specialty_id"] == specialty_id]

    # добавляем введённые КЦП и количество внебюджетников
    if kcp_manual:
        # TODO: добавить проверку на корректность введённых данных
        kcp_dict = {int(k): v for k, v in kcp_manual.items()}
        df_spec["kcp"] = df_spec["kcp"].fillna(df_spec["year"].map(kcp_dict)).astype("Int64")
    elif kcp_growth_pct:
        coeff = 1 + kcp_growth_pct / 100
        # считаем кумулятивное количество пропусков (это же степень для коэффициента прироста)
        pows = df_spec["kcp"].isna().cumsum()
        # протягиваем последнее известное значение КЦП
        kcp_last = df_spec["kcp"].dropna().iloc[-1]
        # умножаем на коэффициент прироста
        df_spec["kcp"] = np.where(df_spec["kcp"].isna(), kcp_last * (coeff**pows), df_spec["kcp"])
        df_spec["kcp"] = np.ceil(df_spec["kcp"]).astype(int)
    else:
        raise_error("Должен быть передан один из параметров: kcp_manual или kcp_growth_pct")
    
    # заполняем зачисленных как КЦП + платные места
    if paid_manual:
        paid_dict = {int(k): v for k, v in paid_manual.items()}
        df_spec["enrolled"] = df_spec["enrolled"].fillna(
            df_spec["kcp"] + df_spec["year"].map(paid_dict)
        ).astype("Int64") 
    elif paid_growth_pct:
        coeff = 1 + paid_growth_pct / 100
        # считаем кумулятивное количество пропусков (это же степень для коэффициента прироста)
        pows = df_spec["enrolled"].isna().cumsum()
        # протягиваем последнее известное значение КЦП
        last_values = df_spec.dropna().iloc[-1]
        paid_last = last_values["enrolled"] - last_values["kcp"]
        # умножаем на коэффициент прироста
        df_spec["enrolled"] = np.where(
            df_spec["enrolled"].isna(),
            # мы не зачислим больше, чем общее количество заявлений
            # TODO: считать реальное количество абитуриентов (часть может уйти на более приоритетные специальности)
            np.minimum(
                df_spec["applications"],
                df_spec["kcp"] + paid_last * (coeff**pows)
            ),
            df_spec["enrolled"]
        )
        df_spec["enrolled"] = np.ceil(df_spec["enrolled"]).astype(int)
    else:
        raise_error("Должен быть передан один из параметров: paid_manual или paid_growth_pct")

    # считаем показатели спроса
    df_demand = _calc_demand(df, forecast_range, weights)

    # считаем конверсию из заявлений в бюджетные и платные места на истории
    df_spec["paid"] = np.where(
        df_spec["enrolled"] - df_spec["kcp"] > 0,
        df_spec["enrolled"] - df_spec["kcp"], 
        0
    )

    df_history = df_spec[df_spec["year"] < forecast_range[0]]

    df_history["conversion_budget"] = np.where(
        df_history["applications"] > 0,
        df_history["kcp"] / df_history["applications"],
        0
    )
    df_history["conversion_paid"] = np.where(
        df_history["applications"] > 0,
        (df_history["paid"]) / df_history["applications"],
        0
    )
    c_budget = df_history["conversion_budget"].mean()
    c_paid = df_history["conversion_paid"].mean()

    df_spec = pd.merge(df_spec, df_history[["specialty_id", "year", "conversion_budget", "conversion_paid"]], how="left", on=["specialty_id", "year"])

    df_spec["kcp_pred"] = np.where(
        df_spec["year"] < forecast_range[1],
        np.nan,
        c_budget * df_spec["applications"]
    )
    df_spec["paid_pred"] = np.where(
        df_spec["year"] < forecast_range[1],
        np.nan,
        (c_paid * df_spec["applications"])
    )
    df_spec["kcp_pred"] = np.ceil(df_spec["kcp_pred"]).astype("Int64")
    df_spec["paid_pred"] = np.ceil(df_spec["paid_pred"]).astype("Int64")

    # создаём таблицу для отчёта
    last_year = df_spec[df_spec["year"] == forecast_range[1]].iloc[0].to_dict()
    balance_budget = round(last_year["kcp_pred"] / last_year["kcp"], 2) if last_year["kcp"] > 0 else None
    balance_paid = round(last_year["paid_pred"] / last_year["paid"], 2) if last_year["paid"] > 0 else None
    table_map = {
        "kcp_input": int(last_year["kcp"]),
        "paid_input": int(last_year["paid"]),
        "applications_pred": int(last_year["applications"]),
        "conversion_budget": round(c_budget, 4),
        "conversion_paid": round(c_paid, 4),
        "kcp_pred": int(last_year["kcp_pred"]),
        "paid_pred": int(last_year["paid_pred"]),
        "balance_budget": balance_budget,
        "balance_paid": balance_paid
    }

    return df_demand, table_map


def _calc_demand(df: pd.DataFrame, forecast_range: tuple[int, int], weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Считает показатели спроса всех специальностей.

    D = w1 * D1 + w2 * D2, где:
    * D1 - нормализованная доля рынка по заявлениям
    * D2 - нормализованный прирост заявлений

    Значения по умолчанию:
    * w1 = 0.7
    * w2 = 0.3
    """
    if weights is None:
        weights = {"w1": 0.7, "w2": 0.3}
    df = df.copy()

    # D1 - доля рынка
    # вычисляем разницу с медианой    
    df["apps_diff"] = _normalize_diff(df)

    # D2 - прирост заявлений
    df["apps_growth"] = _smape_normalized_diff(df)

    # D - итог
    df["demand"] = weights["w1"] * df["apps_diff"] + weights["w2"] * df["apps_growth"]

    return df[["specialty_id", "year", "demand"]]

def _smape_normalized_diff(df, k=-5) -> np.ndarray:
    """Вычисление нормализованного изменения роста по sMAPE от 0 до 1.

    Вычисление прироста по sMAPE:
    * Δx = -inf -> sMAPE = -2
    * Δx = 0 -> sMAPE = 0
    * Δx = inf -> sMAPE = 2

    Нормализация:
    * sMAPE = -2 -> result = 0
    * sMAPE = 0 -> result = 0.5
    * sMAPE = 2 -> result = 1

    Метод sMAPE позволяет вычислить прирост какого-либо количества и сжать его в диапазон [-2, 2].
    Полученное значение нормализуется в диапазон [0, 1] и отображает силу роста.

    Нормализация через сигмоиду приводит результат в диапазон [0, 1] и делает S-образный график, 
    быстрее устремляя значения в 0 и в 1, чем обычная линейная функция.

    Args:
        df: Исходный DataFrame.
        k: Коэффициент изгиба. Чем меньше, тем быстрее стремление к 0 или 1.
    """
    df = df.copy()

    # добавляем значение предыдущего столбца (группируя по специальностям)
    df["prev"] = df.groupby("specialty_id")["applications"].transform(lambda x: x.shift(1))
    
    # числитель и знаменатель для вычисления среднего роста по sMAPE
    numerator = df["applications"] - df["prev"]
    denominator = (df["applications"] + df["prev"]) / 2

    # обрабатываем крайние случаи
    conditions = [
        df["prev"].isna(),                            # первая строка (не можем вычислить предыдущее)
        (df["applications"] == 0) & (df["prev"] == 0) # оба значения нулевые
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

def _normalize_diff(df: pd.DataFrame, k=2) -> np.ndarray:
    """Нормализация разницы со средним в диапазон [0, 1].

    Нормализация:
    * x = 0 -> result = 0
    * x = mean -> result = 0.5
    * x = inf -> result = 1

    Args:
        df: Исходный DataFrame.
        k: Коэффициент изгиба. Чем больше, тем больше изгиб и быстрее стремление к 0 или 1.

    Returns:
        np.ndarray
    """
    df = df.copy()
    df["median"] = df.groupby("year")["applications"].transform("median")

    # возведение в степень прижимает значение к 0 до среднего и к 1 после среднего
    return np.where(
        df["applications"] == 0,
        0,
        df["applications"]**k / (df["applications"]**k + df["median"]**k)
    )

async def _forecast_last(df: pd.DataFrame, history_range: tuple[int, int], forecast_range: tuple[int, int]) -> pd.DataFrame:
    """Прогнозирует количество заявлений, дублируя показатели за прошлый год.
    
    Если количество прогнозных лет больше 1, показатели дублируются (всё время берутся показатели из последнего года истории).
    """
    forecast_df = df.groupby("specialty_id", as_index=False)[["specialty_id", "year", "applications"]].last()
    forecast_df["year"] = forecast_range[0]
    
    new_rows = []
    current_df = forecast_df.copy()

    for year in range(forecast_range[0] + 1, forecast_range[1] + 1):
        current_df = current_df.copy()
        current_df["year"] = year
        new_rows.append(current_df)

    forecast_df = pd.concat([forecast_df] + new_rows, ignore_index=True)
    forecast_df = forecast_df.sort_values(["specialty_id", "year"]).reset_index(drop=True)

    res = pd.concat([df, forecast_df], ignore_index=True)
    res = res.sort_values(["specialty_id", "year"]).reset_index(drop=True)

    return res

async def _forecast_sma(df: pd.DataFrame, history_range: tuple[int, int], forecast_range: tuple[int, int], sma_window: int) -> pd.DataFrame:
    """Прогнозирует количество заявлений с помощью взятия среднего за последние n лет."""
    # проверяем, можем ли мы найти среднее за sma_window лет
    max_window = history_range[1] - history_range[0] + 1
    if sma_window > max_window:
        raise_error(f"Введено слишком большое значение sma_window для исторического диапазона {history_range}: {sma_window}. Допустимый максимум: {max_window}")

    for year in range(forecast_range[0], forecast_range[1] + 1):
        available_data = df[df["year"] < year].sort_values("year")
        # вычисляем динамическое окно: берём n последних реальных лет, где есть данные
        window_data = available_data.groupby("specialty_id").tail(sma_window)
        cur_forecast = window_data.groupby("specialty_id", as_index=False)["applications"].mean()
        cur_forecast["applications"] = np.ceil(cur_forecast["applications"]).astype(int)
        cur_forecast["year"] = year

        df = pd.concat([df, cur_forecast], ignore_index=True)
    
    df = df.sort_values(["specialty_id", "year"]).reset_index(drop=True)

    return df

async def _forecast_demographic(df: pd.DataFrame, history_range: tuple[int, int], forecast_range: tuple[int, int]) -> pd.DataFrame:
    """Прогнозирует количество заявлений на основе демографических показателей 18 лет назад (т.к. поступают в среднем в 18 лет)."""
    query = """
        SELECT b.year, b.births
        FROM public.birth_rate AS b
        ORDER BY b.year;
    """
    df_births = await fetch_query_to_df(query)

    births_map = dict(zip(df_births["year"], df_births["births"]))

    available_data = df.loc[df["year"] <= history_range[1], ["specialty_id", "year", "applications"]].copy()
    # берём последний год, где есть данные
    current_df = available_data.groupby("specialty_id", as_index=False)[["year", "applications"]].last()
    new_rows = []

    for next_year in range(forecast_range[0], forecast_range[1] + 1):
        current_df = current_df.copy()

        births_next = births_map.get(next_year - 18, 0)
        births_base = current_df["year"].map(lambda y: births_map.get(y - 18, 0))
        birth_coeffs = births_next / births_base

        current_df["applications"] = np.ceil(
            current_df["applications"] * birth_coeffs
        ).astype(int)

        current_df["year"] = next_year
        new_rows.append(current_df)

    result_df = pd.concat([df] + new_rows, ignore_index=True)
    result_df = result_df.sort_values(["specialty_id", "year"]).reset_index(drop=True)

    return result_df

async def _forecast_exp_smoothing(df: pd.DataFrame, history_range: tuple[int, int], forecast_range: tuple[int, int], alpha: float = 0.7) -> pd.DataFrame:
    """Предсказывает основные показатели методом экспоненциального сглаживания.

    Формула: Ŷ_t = α * Y_{t-1} + (1 - α) * Ŷ_{t-1}, где 
    * t - год
    * α - коэффициент сглаживания (по умолчанию 0.7)

    Note: эффективен только для прогноза на 1 год вперёд. 
    При вводе большего количества лет прогноз остаётся тем же, что и на 1 год вперёд.
    """
    df_history = df[df["year"] <= history_range[1]].copy()
    
    # считаем прогноз Ŷ_t на истории
    df_history["applications_pred"] = df_history.groupby("specialty_id")["applications"].transform(
        lambda x: x.ewm(alpha=alpha, adjust=False).mean().shift(1)
    )

    # прогноз на первый год - реальное значение Y_t этого же года
    df_history["applications_pred"] = df_history["applications_pred"].fillna(df_history["applications"])

    # берём последний год, где есть данные
    last_data = df_history.groupby("specialty_id", as_index=False).last()
    # вычисляем прогноз на первый год
    first_forecast = np.ceil(
        alpha * last_data["applications"] + (1 - alpha) * last_data["applications_pred"]
    ).astype(int)
    
    # дублируем прогноз для всех прогнозных лет
    new_rows = []
    for next_year in range(forecast_range[0], forecast_range[1] + 1):
        cur_df = pd.DataFrame({
            "specialty_id": last_data["specialty_id"],
            "year": next_year,
            "applications": first_forecast
        })
        new_rows.append(cur_df)
    
    result_df = pd.concat([df] + new_rows, ignore_index=True)
    result_df = result_df.sort_values(["specialty_id", "year"]).reset_index(drop=True)

    return result_df