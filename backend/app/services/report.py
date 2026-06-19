import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import io
from app.settings import REPORTS_DIR, REPORTS_URL
from typing import Tuple
from app.database import fetch_query_to_df
from datetime import date, datetime
from app.models import Report
from sqlalchemy.ext.asyncio import AsyncSession

async def make_report(df: pd.DataFrame, table_map: dict[str, int | float], input_specialty: str, method: str, history_range: Tuple[int, int], forecast_range: Tuple[int, int], session: AsyncSession):
    """Создаёт HTML-отчёт о востребованности специальности и сохраняет в backend/data/reports."""
    method_df = await fetch_query_to_df("SELECT id, slug, name FROM public.forecast_methods WHERE name = :name", {"name": method})
    method_id = method_df["id"].values[0]
    method_slug = method_df["slug"].values[0]
    method_name = method_df["name"].values[0]
    
    # парсим ввод специальности
    code = input_specialty.split(" ")[0]
    spec_df = await fetch_query_to_df(f"SELECT id, name FROM public.specialties WHERE code = '{code}'")
    specialty_id = spec_df["id"].values[0]
    specialty_name = spec_df["name"].values[0]

    # определяем года истории и прогноза
    start_year = history_range[0]
    cur_year = history_range[1]
    end_year = forecast_range[1]

    # добавляем перцентили
    df["demand_percentile"] = df.groupby("year")["demand"].rank(pct=True)

    # находим указанную специальность
    df_spec = df[df["specialty_id"] == specialty_id]

    # определяем текущий и прогнозируемый уровень спроса
    cur_demand_data = _define_demand_level(df[df["year"] == cur_year], specialty_id)
    future_demand_data = _define_demand_level(df[df["year"] == end_year], specialty_id)

    if cur_demand_data[0] == "Не определён":
        cur_demand_html = f"Не определён"
    else:
        cur_demand_html = f"<strong>{cur_demand_data[0]}</strong> ({cur_demand_data[1][0]}-е место из {cur_demand_data[1][1]})"
    if future_demand_data[0] == "Не определён":
        future_demand_html = f"Не определён"
    else:
        future_demand_html = f"<strong>{future_demand_data[0]}</strong> ({future_demand_data[1][0]}-е место из {future_demand_data[1][1]})"

    # определяем стабильность спроса за всё время
    demand_stability = _define_stability(
        df[(df["year"] >= start_year) & (df["year"] <= end_year)],
        specialty_id
    )
    if demand_stability[0] == "Не определена":
        demand_stability_html = "Не определена"
    else:
        demand_stability_html = f"<strong>{demand_stability[0]}</strong> ({demand_stability[1][0]}-е место из {demand_stability[1][1]} по стабильности)"

    # строим динамику спроса
    _plot_trend(
        df_spec[(df_spec["year"] >= start_year) & (df_spec["year"] <= cur_year)],
        df_spec[(df_spec["year"] >= cur_year) & (df_spec["year"] <= end_year)],
    )
    demand_plot = _plot_to_base64()

    # создаем и заполняем основную таблицу
    kcp_input = table_map.get("kcp_input_show") if table_map.get("kcp_input_show") is not None else "Н/Д"
    paid_input = table_map.get("paid_input_show") if table_map.get("paid_input_show") is not None else "Н/Д"
    apps_pred = table_map.get("applications_pred") if table_map.get("applications_pred") is not None else "Н/Д"
    kcp_opt = table_map.get("kcp_pred") if table_map.get("kcp_pred") is not None else "Н/Д"
    paid_opt = table_map.get("paid_pred") if table_map.get("paid_pred") is not None else "Н/Д"
    balance_budget = table_map.get("balance_budget") if table_map.get("balance_budget") is not None else "Н/Д"
    balance_paid = table_map.get("balance_paid") if table_map.get("balance_paid") is not None else "Н/Д"
    data = {
        "КЦП (ввод)": kcp_input,
        "Платные (ввод)": paid_input,
        "Заявления (прогноз)": apps_pred,
        "КЦП (оптимум)": kcp_opt,
        "Платные (оптимум)": paid_opt,
        "Баланс (бюджет)": balance_budget,
        "Баланс (платные)": balance_paid
    }
    df_table = pd.DataFrame([data], index=["Значение"])

    # задаём рекомендации
    budget_recs_html, paid_recs_html = "Для вас нет рекомендаций", "Для вас нет рекомендаций"
    balance_budget = table_map["balance_budget"]
    balance_paid = table_map["balance_paid"]
    
    budget_recs_html = _get_budget_recommendations(balance_budget, table_map["kcp_input"], table_map["kcp_pred"])
    paid_recs_html = _get_paid_recommendations(balance_paid, table_map["paid_input"], table_map["paid_pred"])


    # форматируем таблицу
    html_table = _format_html_table(df_table)

    # создаем лепестковую диаграмму
    #_plot_radar(spec_cur, spec_last)
    #radar_plot = _plot_to_base64()

    # задаём понятный вид годам в начале отчета
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
        method_name=method_name,
        history_data=history_data,
        forecast_data=forecast_data,
        cur_demand=cur_demand_html,
        future_demand=future_demand_html,
        demand_stability=demand_stability_html,
        demand_plot=demand_plot,
        table=html_table,
        budget_recommendations=budget_recs_html,
        paid_recommendations=paid_recs_html
    )
    
    # определяем название и путь файла
    timestamp = datetime.now()
    # TODO: сделать хэширование отчетов и поиск похожих
    filename = f"{_rus_to_eng(specialty_name)}-{method_slug}-{timestamp.strftime("%Y-%m-%d-%H-%M-%S")}.html"
    file_path = f"{REPORTS_DIR}/{filename}"
    url_path = f"{REPORTS_URL}/{filename}"

    # сохраняем отчет в файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # создаем запись в БД
    report = Report(
        specialty_id=specialty_id,
        method_id=method_id,
        start_year=start_year,
        current_year=cur_year,
        end_year=end_year,
        url=url_path,
        created_at=timestamp
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

def _plot_trend(df_history: pd.DataFrame, df_cur_future: pd.DataFrame):
    # сначала прогнозные, чтобы они были на заднем фоне
    plt.plot(df_cur_future["year"], df_cur_future["demand_percentile"], label="Прогноз", color="#d62728", marker="o", linestyle="--")
    plt.plot(df_history["year"], df_history["demand_percentile"], label="Факт", color="#1f77b4", marker="s", markersize=7, linestyle="-")

    # переводим числа в категории, ось y
    plt.yticks([0.0, 0.25, 0.5, 0.75, 1.0], labels=[])
    label_positions = [0.125, 0.375, 0.625, 0.875] # середины категорий
    labels = ["Низкий", "Средний", "Высокий", "Очень высокий"]
    plt.gca().set_yticks(label_positions, minor=True)
    plt.gca().set_yticklabels(labels, minor=True)
    plt.gca().tick_params(axis='y', which='minor', length=0)
    plt.ylabel("Уровень спроса")

    # ось x
    plt.xlabel("Год")
    from matplotlib.ticker import MaxNLocator
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    
    plt.title("Динамика спроса")
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
    if df[df["specialty_id"] == specialty_id].shape[0] == 0:
        return "Не определён", (0, 0)
    
    df = df.copy()
    df["percentile"] = df["demand"].rank(pct=True)
    percentile = df.loc[df["specialty_id"] == specialty_id, "percentile"].values[0]

    df = df.sort_values("demand", ascending=False).reset_index(drop=True)
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
    if df[df["specialty_id"] == specialty_id].shape[0] == 0:
        return "Не определена", (0, 0)
    
    df_std = df.groupby("specialty_id")["demand"].std().reset_index(name="std")
    df_std["percentile"] = df_std["std"].rank(pct=True)
    percentile = df_std.loc[df_std['specialty_id'] == specialty_id, 'percentile'].values[0]

    df_std = df_std.sort_values("std").reset_index(drop=True)
    place = df_std[df_std["specialty_id"] == specialty_id].index[0] + 1
    all_places = df_std.shape[0]
    place_res = (place, all_places)

    if percentile < 0.25:
        return "Очень высокая", place_res
    if percentile < 0.5:
        return "Высокая", place_res
    if percentile < 0.75:
        return "Средняя", place_res
    return "Низкая", place_res

def _get_place(df: pd.DataFrame, specialty_id: int, indicator: str) -> str:
    df = df.copy()
    df = df.sort_values(indicator, ascending=False).reset_index(drop=True)
    place = df[df["specialty_id"] == specialty_id].index[0] + 1
    all_places = df.shape[0]
    return f"{place}&nbsp;из&nbsp;{all_places}"

def _get_trend(cur_val: float, forecast_val: float, years: int) -> str:
    # считаем среднегодовой прирост в %, обрабатывая крайние случаи
    eps = 0.0001
    if -eps < cur_val < eps and -eps < forecast_val < eps:
        return f"Стабилен<br>(0% г/г)"
    if -eps < cur_val < eps and forecast_val < -eps:
        return "Падение"
    if -eps < cur_val < eps and forecast_val > eps:
        return "Рост"
    
    cagr = ((forecast_val / cur_val) ** (1 / years) - 1) * 100

    if cagr < -5:
        return f"Падение<br>({round(cagr, 1)}% г/г)"
    if -5 <= cagr < -0.05:
        return f"Стабилен<br>({round(cagr, 1)}% г/г)"
    if -0.05 <= cagr < 0.05:
        return f"Стабилен<br>(0% г/г)"
    if 0.05 <= cagr < 5:
        return f"Стабилен<br>(+{round(cagr, 1)}% г/г)"
    
    return f"Рост<br>(+{round(cagr, 1)}% г/г)"

def _get_budget_recommendations(balance, actual, pred):
    """Возвращает рекомендации для КЦП на основе баланса спроса и предложения в html-формате."""
    if actual == 0:
        if pred == 0:
            recs = "<strong>КЦП</strong>: Оптимальное количество<br>Рекомендуется оставить число бюджетных мест без изменений."
        # FIXME: используется хардкод
        elif pred < 10:
            recs = f"<strong>КЦП</strong>: <strong>Недостаток мест</strong><br>Рекомендуется увеличить число бюджетных мест на {pred}."
        else:
            recs = f"<strong>КЦП</strong>: <strong>Существенный недостаток мест</strong><br>Рекомендуется увеличить число бюджетных мест на {pred}."
        return f"<p>{recs}</p>"
    if pred == 0:
        # FIXME: используется хардкод
        if actual < 10:
            recs = f"<strong>КЦП</strong>: <strong>Избыток мест</strong><br>Рекомендуется сократить число бюджетных мест на {actual}."
        else:
            recs = f"<strong>КЦП</strong>: <strong>Существенный избыток мест</strong><br>Рекомендуется сократить число бюджетных мест на {actual}."
        return f"<p>{recs}</p>"

    add = pred - actual
    add_pct = round((pred - actual) / actual * 100, 1)
    sub = actual - pred
    sub_pct = round((pred - actual) / actual * 100, 1)
    if balance >= 1.5:
        recs = f"<strong>КЦП</strong>: <strong>Существенный недостаток мест</strong><br>Рекомендуется увеличить число бюджетных мест на {add} (+{add_pct}%)."
    elif 1.1 <= balance < 1.5:
        recs = f"<strong>КЦП</strong>: <strong>Недостаток мест</strong><br>Рекомендуется увеличить число бюджетных мест на {add} (+{add_pct}%)."
    elif 0.9 < balance < 1.1:
        recs = f"<strong>КЦП</strong>: Оптимальное количество<br>Рекомендуется оставить число бюджетных мест без изменений."
    elif 0.5 < balance <= 0.9:
        recs = f"<strong>КЦП</strong>: <strong>Избыток мест</strong><br>Рекомендуется сократить число бюджетных мест на {sub} ({sub_pct}%)."
    else: # <= 0.5
        recs = f"<strong>КЦП</strong>: <strong>Существенный избыток мест</strong><br>Рекомендуется сократить число бюджетных мест на {sub} ({sub_pct}%)."

    return f"<p>{recs}</p>"

def _get_paid_recommendations(balance, actual, pred):
    """Возвращает рекомендации для платных мест на основе баланса спроса и предложения в html-формате."""
    if actual == 0:
        if pred == 0:
            recs = "<strong>Платные места</strong>: Оптимальное количество<br>Рекомендуется оставить число бюджетных мест без изменений."
        # FIXME: используется хардкод
        elif pred < 10:
            recs = f"<strong>Платные места</strong>: <strong>Недостаток мест</strong><br>Рекомендуется увеличить число бюджетных мест на {pred}."
        else:
            recs = f"<strong>Платные места</strong>: <strong>Существенный недостаток мест</strong><br>Рекомендуется увеличить число бюджетных мест на {pred}."
        return f"<p>{recs}</p>"
    if pred == 0:
        # FIXME: используется хардкод
        if actual < 10:
            recs = f"<strong>Платные места</strong>: <strong>Избыток мест</strong><br>Рекомендуется сократить число бюджетных мест на {actual}."
        else:
            recs = f"<strong>Платные места</strong>: <strong>Существенный избыток мест</strong><br>Рекомендуется сократить число бюджетных мест на {actual}."
        return f"<p>{recs}</p>"
    
    add = pred - actual
    add_pct = round((pred - actual) / actual * 100, 1)
    sub = actual - pred
    sub_pct = round((pred - actual) / actual * 100, 1)
    if balance >= 1.5:
        recs = f"<strong>Платные места</strong>: <strong>Существенный недостаток</strong><br>Рекомендуется увеличить число платных мест на {add} (+{add_pct}%)."
    elif 1.1 <= balance < 1.5:
        recs = f"<strong>Платные места</strong>: <strong>Недостаток</strong><br>Рекомендуется увеличить число платных мест на {add} (+{add_pct}%)."
    elif 0.9 < balance < 1.1:
        recs = f"<strong>Платные места</strong>: Оптимальное количество<br>Рекомендуется оставить число платных мест без изменений."
    elif 0.5 < balance <= 0.9:
        recs = f"<strong>Платные места</strong>: <strong>Избыток</strong><br>Рекомендуется сократить число платных мест на {sub} ({sub_pct}%)."
    else: # <= 0.5
        recs = f"<strong>Платные места</strong>: <strong>Существенный избыток</strong><br>Рекомендуется сократить число платных мест на {sub} ({sub_pct}%)."

    return f"<p>{recs}</p>"

def _format_html_table(df: pd.DataFrame) -> str:
    """
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
    """

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
        .centered-table td {
            white-space: nowrap;
        }
    </style>
    """

    return html_style + df.to_html(classes='centered-table', justify='center', escape=False)

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
            <li>Метод прогнозирования: {params["method_name"]}</li>
        </ul>

        <h3>Показатель спроса</h3>
        <ul>
            <li>Текущий уровень: {params["cur_demand"]}</li>
            <li>Ожидаемый уровень: {params["future_demand"]}</li>
            <li>Стабильность показателя: {params["demand_stability"]}</li>
        </ul>
        <p class="text-secondary">
        Часть данных отсутствует, поэтому количество специальностей может отличаться и спрос может быть не определён.
        </p>

        <p>Ниже приведена динамика изменения спроса:</p>
        <div class="plot-container">
            <img src="data:image/png;base64,{params["demand_plot"]}" alt="График">
        </div>
        <p class="text-secondary">
        Т.к. показатель считает разницу с предыдущим годом, то за первый год истории нельзя посчитать спрос.
        </p>

        <h3>Прогноз, баланс спроса и предложения</h3>
        {params["table"]}

        <h3>Выводы и рекомендации</h3>
        {params["budget_recommendations"]}
        {params["paid_recommendations"]}

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