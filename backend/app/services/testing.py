from app.database import fetch_query_to_df, fetch_query_to_scalar
from app.services.forecast import make_forecast
import pandas as pd
from app.services.utils import raise_error

async def get_model_errors(methods: list[str] | None = None):
    """Тестирует модель и выдаёт ошибки модели по wMAPE.
    
    Args:
        methods - список методов прогнозирования (по умолчанию все)
    """
    df_methods = await fetch_query_to_df("SELECT slug, name FROM public.forecast_methods")
    available = df_methods["name"].tolist()
    if not methods:
        methods = available
    else:
        non_existing = set(methods) - set(available)
        if non_existing:
            raise_error(f"Методы {', '.join(non_existing)} не существуют. Доступные: {available}")
    
    start = await fetch_query_to_scalar("SELECT MIN(year) FROM public.application_stats")
    end = await fetch_query_to_scalar("SELECT MAX(year) FROM public.application_stats")
    if start is None or end is None:
        raise_error("Таблица application_stats не заполнена", status_code=500)
    start, end = int(start), int(end)

    metrics = []
    for method in methods:
        metric = {"method": method, "errors": {y: None for y in range(start + 1, end + 1)}}
        for test_year in range(start + 1, end + 1):
            # если метод - SMA, нужно проверить размер окна
            if method.startswith("Скользящее среднее") and int(method.split(" ")[-2]) > test_year - start:
                continue

            query = """
                SELECT specialty_id, applications
                FROM public.application_stats
                WHERE year = :test_year AND applications IS NOT NULL 
            """
            # получаем фактические данные
            raw_exp = await fetch_query_to_df(query, params={"test_year": test_year})
            df_expected = raw_exp.sort_values("specialty_id").reset_index(drop=True)

            # прогнозируем
            raw_pred, _ = await make_forecast("all", method, (start, test_year - 1), (test_year, test_year))
            df_predicted = (
                raw_pred.loc[raw_pred["year"] == test_year, ["specialty_id", "applications"]]
                .sort_values("specialty_id").reset_index(drop=True))
            
            # объединяем
            df_total = pd.merge(df_expected, df_predicted, on="specialty_id", how="inner", suffixes=("_exp", "_pred"))
            
            # находим взвешенную ошибку в процентах (Weighted Mean Absolute Percentage Error)
            # она хорошо сглаживает мелкие специальности, у которых большая ошибка
            # формула: sum(|Факт - Прогноз|) / sum(Факт)
            wmape = (
                (df_total["applications_exp"] - df_total[f"applications_pred"]).abs().sum() / 
                df_total[f"applications_exp"].sum()
            ) * 100
            
            metric["errors"][test_year] = round(wmape, 1)

        metrics.append(metric)
    
    return metrics