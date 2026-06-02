import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import io
from app.settings import REPORTS_DIR, REPORTS_URL
from typing import Tuple
from app.database import fetch_query_to_df
from datetime import date
from app.models import Report
from sqlalchemy.ext.asyncio import AsyncSession

async def make_report(df: pd.DataFrame, input_specialty: str, method: str, history_range: Tuple[int, int], forecast_range: Tuple[int, int], session: AsyncSession):
    """Создаёт HTML-отчёт о востребованности специальности и сохраняет в backend/data/reports."""
    # отображаем метод в читаемом формате
    old_method = method
    if method.startswith("sma_"):
        y = int(method[4:])
        if y == 1:
            method = "Скользящее среднее за 1 год"
        elif 2 <= y <= 4:
            method = f"Скользящее среднее за {y} года"
        else:
            method = f"Скользящее среднее за {y} лет"
    elif method == "demographic":
        method = "Демографический"
    elif method == "exponential_smoothing":
        method = "Экспоненциальное сглаживание"
    
    # парсим ввод специальности
    code = input_specialty.split(" ")[0]
    spec_df = await fetch_query_to_df(f"SELECT id, name FROM public.specialties WHERE code = '{code}'")
    specialty_id = spec_df["id"].values[0]
    specialty_name = spec_df["name"].values[0]

    # определяем года истории и прогноза
    start_year = history_range[0]
    cur_year = history_range[1]
    end_year = forecast_range[1]
    
    # находим данные по всем специальностям в текущем году
    df_cur = df[df["year"] == cur_year]

    # находим указанную специальность
    df_spec = df[df["specialty_id"] == specialty_id]
    spec_hist = df_spec[(df_spec["year"] >= start_year) & (df_spec["year"] <= cur_year)]
    spec_cur = df_spec[df_spec["year"] == cur_year]
    spec_fut = df_spec[(df_spec["year"] >= cur_year + 1) & (df_spec["year"] <= end_year)]
    spec_last = df_spec[df_spec["year"] == end_year]
    spec_cur_fut = pd.concat([spec_cur, spec_fut], ignore_index=True) # текущий год + прогноз

    # определяем текущий и прогнозируемый уровень востребованности
    cur_demand = _define_demand_level(df[df["year"] == cur_year], specialty_id)
    future_demand = _define_demand_level(df[df["year"] == end_year], specialty_id)

    # определяем стабильность прогноза (по истории)
    stability = _define_stability(
        df[(df["year"] >= start_year) & (df["year"] <= cur_year)],
        specialty_id
    )

    # строим динамику востребованности
    _plot_trend(spec_hist, spec_cur_fut, "D", "Год", "Востребованность", "Динамика востребованности")
    demand_plot = _plot_to_base64()

    # создаем основную таблицу
    index=["Доля внебюджетников", "Заявления", "Конкурс", "КЦП"]
    columns = [f"Текущее значение ({cur_year} год)", "Динамика за год", f"Прогноз ({end_year} год)", "Место в вузе", "Статус тренда"]
    df_table = pd.DataFrame(index=index, columns=columns)

    # заполняем таблицу
    for row, ind in zip(index, ["D1", "applications", "competition", "kcp"]):
        df_table.loc[row, f"Текущее значение ({cur_year} год)"] = spec_cur[ind].values[0]
        df_table.loc[row, "Динамика за год"] = spec_cur[ind].values[0] - spec_hist[spec_hist["year"] == cur_year - 1][ind].values[0]
        df_table.loc[row, f"Прогноз ({end_year} год)"] = spec_fut[spec_fut["year"] == end_year][ind].values[0]
        place = _get_place(df_cur, specialty_id, ind)
        df_table.loc[row, "Место в вузе"] = f"{place[0]} из {place[1]}"
        trend = _get_trend(spec_cur[ind].values[0], spec_last[ind].values[0], end_year - cur_year)
        df_table.loc[row, "Статус тренда"] = f"{trend[0]} ({trend[1]})"

    # форматируем таблицу
    html_table = _format_html_table(df_table)

    # создаем лепестковую диаграмму
    _plot_radar(spec_cur, spec_last)
    radar_plot = _plot_to_base64()

    # создаем понятный вид
    if start_year == cur_year:
        history_data = f"{start_year} г."
    else:
        history_data = f"{start_year} - {cur_year} г."
    if cur_year + 1 == end_year:
        forecast_data = f"{cur_year + 1} г."
    else:
        forecast_data = f"{cur_year + 1} - {end_year} г."

    # создаем html-контент
    html_content = _make_html_content(
        specialty_name=specialty_name,
        method=method,
        history_data=history_data,
        forecast_data=forecast_data,
        cur_demand=cur_demand,
        future_demand=future_demand,
        stability=stability,
        demand_plot=demand_plot,
        table=html_table,
        radar_plot=radar_plot
    )
    
    # определяем название и путь файла
    filename = f"{_rus_to_eng(specialty_name)}-{old_method}-{start_year}-{cur_year}-{cur_year + 1}-{end_year}.html"
    file_path = f"{REPORTS_DIR}/{filename}"
    url_path = f"{REPORTS_URL}/{filename}"

    # сохраняем отчет в файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # создаем запись в БД
    report = Report(
        specialty_id=specialty_id,
        method=old_method,
        start_year=start_year,
        current_year=cur_year,
        end_year=end_year,
        url=url_path
    )
    session.add(report)

    await session.commit()
    
    return url_path

def _plot_to_base64():
    """Сохраняет matplotlib-график в виде base64-строки."""
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return base64.b64encode(buf.read()).decode('utf-8')

def _plot_trend(history: pd.DataFrame, future: pd.DataFrame, indicator: str, xlabel: str, ylabel: str, title: str):
    # сначала прогнозные, чтобы они были на заднем фоне
    plt.plot(future["year"], future[indicator], label="Прогноз", color="#d62728", marker="o", linestyle="--")
    plt.plot(history["year"], history[indicator], label="Факт", color="#1f77b4", marker="s", markersize=7, linestyle="-")

    plt.xlabel(xlabel)
    from matplotlib.ticker import MaxNLocator
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)

def _plot_radar(spec_cur: pd.DataFrame, spec_last: pd.DataFrame):
    labels = ["Внебюджетники", "Заявления", "Конкурс", "КЦП"]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    values_1 = [
        spec_cur["D1"].values[0],
        spec_cur["D2"].values[0],
        spec_cur["D3"].values[0],
        spec_cur["D4"].values[0]
    ]
    values_1 += values_1[:1]

    values_2 = [
        spec_last["D1"].values[0],
        spec_last["D2"].values[0],
        spec_last["D3"].values[0],
        spec_last["D4"].values[0]
    ]
    values_2 += values_2[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    # текущие значения
    ax.plot(angles, values_1, color='#1f77b4', linewidth=2, label='Текущие показатели')
    ax.fill(angles, values_1, color='#1f77b4', alpha=0.2)

    # ожидаемые значения
    ax.plot(angles, values_2, color='#ff7f0e', linewidth=2, label='Ожидаемые показатели')
    ax.fill(angles, values_2, color='#ff7f0e', alpha=0.2)

    ax.set_ylim(0, 1)
    _, labels_text = ax.set_thetagrids(np.degrees(angles[:-1]), labels)

    labels_text[0].set_position((0, 0))
    labels_text[0].set_ha('left')

    labels_text[1].set_position((0, 0))
    labels_text[1].set_va('bottom')

    labels_text[2].set_position((0, 0)) 
    labels_text[2].set_ha('right')

    labels_text[3].set_position((0, 0)) 
    labels_text[3].set_va('top') 
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

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
    place_res = (place, all_places)

    if percentile < 0.25:
        return "Очень высокая", place_res
    if percentile < 0.5:
        return "Высокая", place_res
    if percentile < 0.75:
        return "Средняя", place_res
    return "Низкая", place_res

def _get_place(df: pd.DataFrame, specialty_id: int, indicator: str) -> Tuple[int, int]:
    df = df.copy()
    df = df.sort_values(indicator, ascending=False).reset_index(drop=True)
    place = df[df["specialty_id"] == specialty_id].index[0] + 1
    all_places = df.shape[0]
    return place, all_places

def _get_trend(cur_val: float, forecast_val: float, years: int) -> Tuple[str, str]:
    # считаем среднегодовой прирост в %
    cagr = ((forecast_val / cur_val) ** (1 / years) - 1) * 100

    if cagr < -5:
        return "Падение", f"{round(cagr, 1)}% г/г"
    if -5 <= cagr < 0:
        return "Стабилен", f"{round(cagr, 1)}% г/г"
    if 0 <= cagr < 5:
        return "Стабилен", f"+{round(cagr, 1)}% г/г"
    
    return "Рост", f"+{round(cagr, 1)}% г/г"

def _format_html_table(df: pd.DataFrame) -> str:
    for col in range(3):
        val = float(df.iloc[0, col]) * 100
        df.iloc[0, col] = f"{val:.1f}%"
    for col in range(3):
        df.iloc[1, col] = f"{int(float(df.iloc[1, col]))}"
    for col in range(3):
        df.iloc[2, col] = f"{float(df.iloc[2, col]):.1f}"
    for col in range(3):
        df.iloc[3, col] = f"{int(float(df.iloc[3, col]))}"

    for row in range(df.shape[0]):
        if df.iloc[row, 1][0] == "-":
            df.iloc[row, 1] = f"▼{df.iloc[row, 1]:>8}"
        else:
            df.iloc[row, 1] = f"+{df.iloc[row, 1]}"
            df.iloc[row, 1] = f"▲{df.iloc[row, 1]:>8}"

    html_style = """
    <style>
        .centered-table {
            border-collapse: collapse;
            width: 100%;
        }
        .centered-table th, .centered-table td {
            text-align: center !important;
            vertical-align: middle;
            padding: 8px;
        }
    </style>
    """

    return html_style + df.to_html(classes='centered-table', justify='center')

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
            .text-secondary {{ color: #666; font-size: 0.8em; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <h1>Прогноз: {params["specialty_name"]}</h1>

        <h3>Взятые данные</h3>
        <ul>
            <li>Исторические данные: {params["history_data"]}</li>
            <li>Прогнозные данные: {params["forecast_data"]}</li>
            <li>Метод прогнозирования: {params["method"]}</li>
        </ul>

        <h3>Итоговый показатель востребованности</h3>
        <ul>
            <li>Текущий уровень: <strong>{params["cur_demand"][0]}</strong> ({params["cur_demand"][1][0]}-е место из {params["cur_demand"][1][1]})</li>
            <li>Ожидаемый уровень: <strong>{params["future_demand"][0]}</strong> ({params["future_demand"][1][0]}-е место из {params["future_demand"][1][1]})</li>
            <li>Стабильность показателя: <strong>{params["stability"][0]}</strong> ({params["stability"][1][0]}-е место из {params["stability"][1][1]} по стабильности)</li>
        </ul>
        <p class="text-secondary">
        Общее количество специальностей может отличаться, т.к. часть данных отсутствует.
        </p>
        <p>Ниже приведена динамика изменения итоговой востребованности:</p>
        <div class="plot-container">
            <img src="data:image/png;base64,{params["demand_plot"]}" alt="График">
        </div>
        <p class="text-secondary">
        Считаем, что за первый год нельзя посчитать востребованность. Это стартовая точка для будущих лет.
        </p>

        <h3>Базовые показатели и прогноз развития</h3>
        {params["table"]}
        <p class="text-secondary">
        Место в вузе находится среди всех специальностей по указанному показателю. Чем выше показатель, тем выше место.
        </p>

        <h3>Вектор изменения востребованности направления</h3>
        <p>Лепестковая диаграмма ниже отображает текущий и прогнозируемый вклад каждого фактора в итоговый показатель востребованности.</p>
        <div class="plot-container">
            <img src="data:image/png;base64,{params["radar_plot"]}" alt="График">
        </div>
        <div style="font-family: sans-serif; background-color: #f0f7ff; border-left: 4px solid #0066cc; padding: 15px; margin-top: 30px; border-radius: 4px;">
        <p style="margin: 0; font-size: 14px; color: #333333;">
            <strong>Не понятна интерпретация результатов?</strong><br>
            Загляните в раздел <a href="http://localhost:5173/employee/help" style="color: #0066cc; font-weight: bold; text-decoration: none;">"Справка"</a> на главной странице в личном кабинете — там собрана подробная информация.
        </p>
        </div>
        <p><strong>Дата создания:</strong> {date.today().strftime("%d.%m.%Y")}</p>
    </body>
    </html>
    """