import pandas as pd
import matplotlib.pyplot as plt
import base64
import io
from app.settings import BASE_DIR
from typing import Tuple
import asyncio
from app.database import fetch_query_to_df
from datetime import date

async def make_report(
        df: pd.DataFrame, 
        input_specialty: str, 
        history_range: Tuple[int, int], 
        forecast_range: Tuple[int, int]
    ):
    """Создаёт HTML-отчёт о востребованности специальности и сохраняет в backend/data/reports."""
    # парсим ввод специальности
    code = input_specialty.split(" ")[0]
    spec_df = await fetch_query_to_df(f"SELECT id, name FROM public.specialties WHERE code = '{code}'")
    specialty_id = spec_df["id"].values[0]
    specialty_name = spec_df["name"].values[0]
    
    df_history = df[(df["year"] >= history_range[0]) & (df["year"] <= history_range[1])]
    df_cur = df[df["year"] == history_range[1]]
    df_future = df[(df["year"] >= forecast_range[0]) & (df["year"] <= forecast_range[1])]
    df_last = df[df["year"] == forecast_range[1]]

    # определяем текущий и прогнозируемый уровень востребованности
    cur_demand = _define_demand_level(df_cur, specialty_id)
    future_demand = _define_demand_level(df_last, specialty_id)

    # определяем стабильность прогноза (по истории)
    stability = _define_stability(df_history, specialty_id)

    # отражаем статистику по заявлениям
    hist = df_history[df_history["specialty_id"] == specialty_id]
    cur = df_cur[df_cur["specialty_id"] == specialty_id]
    fut = df_future[df_future["specialty_id"] == specialty_id]
    cur_fut = pd.concat([cur, fut], ignore_index=True)

    # сначала прогнозные, чтобы они были на заднем фоне
    plt.plot(cur_fut["year"], cur_fut["applications"], label="Прогноз", color="#d62728", marker="o", linestyle="--")
    plt.plot(hist["year"], hist["applications"], label="Факт", color="#1f77b4", marker="s", markersize=7, linestyle="-")

    plt.xlabel("Год")
    plt.ylabel("Количество заявлений")
    plt.title(f"Динамика заявлений")
    plt.legend()
    plt.grid(True, alpha=0.3)
    apps_plot = _plot_to_base64()

    # создаем html-контент
    html_content = _make_html_content(
        specialty_name=specialty_name,
        cur_demand=cur_demand,
        future_demand=future_demand,
        stability=stability,
        apps_plot=apps_plot
    )
    
    # определяем название и путь файла
    output_path = f"{BASE_DIR}/backend/data/reports/{_rus_to_eng(specialty_name)}.html"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def _plot_to_base64():
    """Сохраняет matplotlib-график в виде base64-строки."""
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return base64.b64encode(buf.read()).decode('utf-8')

def _rus_to_eng(s: str) -> str:
    d = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        "А": "a", "Б": "b", "В": "v", "Г": "g", "Д": "d", "Е": "e", "Ё": "yo",
        "Ж": "zh", "З": "z", "И": "i", "Й": "y", "К": "k", "Л": "l", "М": "m",
        "Н": "n", "О": "o", "П": "p", "Р": "r", "С": "s", "Т": "t", "У": "u",
        "Ф": "f", "Х": "kh", "Ц": "ts", "Ч": "ch", "Ш": "sh", "Щ": "shch",
        "Ъ": "", "Ы": "y", "Ь": "", "Э": "e", "Ю": "yu", "Я": "ya",
        " ": "_"
    }

    return "".join(d.get(c, c) for c in s)

def _define_demand_level(df: pd.DataFrame, specialty_id: int) -> Tuple[str, Tuple[int, int]]:
    df = df.copy()
    df['percentile'] = df["D"].rank(pct=True)
    percentile = df.loc[df['specialty_id'] == specialty_id, 'percentile'].values[0]

    df = df.sort_values("D", ascending=False).reset_index(drop=True)
    place = df[df["specialty_id"] == specialty_id].index[0] + 1
    all_places = df.shape[0]
    place_res = (place, all_places)

    if percentile < 0.25:
        return "Низкий", place_res
    if percentile < 0.5:
        return "Средний", place_res
    if percentile < 0.75:
        return "Высокий", place_res
    return "Очень высокий", place_res

def _define_stability(df: pd.DataFrame, specialty_id: int) -> Tuple[str, Tuple[int, int]]:
    spec_df = df.groupby("specialty_id")["D"].std().reset_index(name="std")
    spec_df["percentile"] = spec_df["std"].rank(pct=True)
    percentile = spec_df.loc[spec_df['specialty_id'] == specialty_id, 'percentile'].values[0]

    spec_df = spec_df.sort_values("std").reset_index(drop=True)
    place = spec_df[spec_df["specialty_id"] == specialty_id].index[0] + 1
    all_places = spec_df.shape[0]
    place_str = f"{place}/{all_places}"
    place_res = (place, all_places)

    if percentile < 0.25:
        return "Очень высокий", place_res
    if percentile < 0.5:
        return "Высокий", place_res
    if percentile < 0.75:
        return "Средний", place_res
    return "Низкий", place_res

def _make_html_content(**params) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Отчёт: {params["specialty_name"]}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; line-height: 1.6; }}
            h1 {{ color: #333; }}
            .plot-container {{ text-align: center; margin: 20px 0; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>Прогноз: {params["specialty_name"]}</h1>

        <p><strong>Текущий спрос: {params["cur_demand"][0]}</strong> ({params["cur_demand"][1][0]}-е место из {params["cur_demand"][1][1]}).</p>

        <p><strong>Прогноз спроса: {params["future_demand"][0]}</strong> ({params["future_demand"][1][0]}-е место из {params["future_demand"][1][1]}).</p>

        <p><strong>Надежность прогноза: {params["stability"][0]}</strong> ({params["stability"][1][0]}-е место из {params["stability"][1][1]} по стабильности).</p>
        
        <div class="plot-container">
            <img src="data:image/png;base64,{params["apps_plot"]}" alt="График">
        </div>
        
        <p><strong>Дата создания:</strong> {date.today().strftime("%d.%m.%Y")}</p>
    </body>
    </html>
    """

async def main():
    from app.services.forecast import make_forecast
    df = await make_forecast("all", "sma_3", (2019, 2023), (2024, 2026))
    res = await make_report(df, "09.03.03 Прикладная информатика", (2019, 2023), (2024, 2026))

if __name__ == "__main__":
    asyncio.run(main())