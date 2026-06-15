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

    errors = []
    indicators_to_rus = {
        "applications": "Заявления",
        "kcp": "КЦП",
        "enrolled": "Зачисленные",
    }
    for method in methods:
        metrics = [
            {"name": "Заявления", "errors": {}},
            {"name": "КЦП", "errors": {}},
            {"name": "Зачисленные", "errors": {}},
        ]
        for test_year in range(start + 1, end + 1):
            # если метод - SMA, нужно проверить размер окна
            if method.startswith("Скользящее среднее") and int(method.split(" ")[-2]) > test_year - start:
                for m in metrics:
                    m["errors"][test_year] = None
                continue

            query = """
                SELECT specialty_id, applications, kcp, enrolled
                FROM public.application_stats
                WHERE year = :test_year 
                    AND applications IS NOT NULL 
                    AND kcp IS NOT NULL 
                    AND enrolled IS NOT NULL
            """
            # получаем фактические данные
            raw_exp = await fetch_query_to_df(query, params={"test_year": test_year})
            df_expected = raw_exp.sort_values("specialty_id").reset_index(drop=True)

            # прогнозируем
            raw_pred = await make_forecast(method, (start, test_year - 1), (test_year, test_year))
            df_predicted = (
                raw_pred[raw_pred["year"] == test_year][["specialty_id", "applications", "kcp", "enrolled"]]
                .sort_values("specialty_id").reset_index(drop=True))
            
            # объединяем
            df_total = pd.merge(df_expected, df_predicted, on="specialty_id", how="inner", suffixes=("_exp", "_pred"))
            
            def get_wmape(col):
                """Находит взвешенную ошибку в процентах (Weighted Mean Absolute Percentage Error).
                
                Хорошо сглаживает мелкие специальности, у которых большая ошибка.
                Формула: sum(|Факт - Прогноз|) / sum(Факт)
                """
                return (abs(df_total[f"{col}_exp"] - df_total[f"{col}_pred"]).sum() / df_total[f"{col}_exp"].sum()) * 100
            
            for col in indicators_to_rus:
                for m in metrics:
                    if m["name"] == indicators_to_rus[col]:
                        m["errors"][test_year] = round(get_wmape(col), 1)
                        break
        
        errors.append({"method": method, "metrics": metrics})
    
    return errors