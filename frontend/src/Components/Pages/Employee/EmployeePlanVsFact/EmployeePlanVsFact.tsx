import { JSX, memo } from 'react';
import styles from './Styles.module.scss';
import { usePlanVsFact } from '@/Hooks/usePlanVsFact';

function PlanVsFactComponent(): JSX.Element {
  const { data, loading, error } = usePlanVsFact();

  if (loading) {
    return <div>Загрузка...</div>;
  }

  if (error) {
    return <div>Ошибка: {error}</div>;
  }

  if (!data || data.length === 0) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Точность модели</h1>
          <p className={styles.subtitle}>Оценка ошибки прогнозирования на исторических данных</p>
        </div>
        <div className={styles.container}>
          <div className={styles.empty}>Данные отсутствуют</div>
        </div>
      </div>
    );
  }

  const years = Array.from(
    new Set(
      data.flatMap((metric) => Object.keys(metric.errors).map(Number))
    )
  ).sort((a, b) => a - b);

  const getErrorClass = (value: number) => {
    if (value > 30) return styles.errorRed;
    if (value > 15) return styles.errorYellow;
    return styles.errorGreen;
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Точность модели</h1>
        <p className={styles.subtitle}>Оценка ошибки прогнозирования на исторических данных</p>
      </div>

      <div className={styles.container}>
        <div className={styles.tableWrapper}>
          <table>
            <thead>
              <tr>
                <th>Метод прогнозирования \ Год</th>
                {years.map((year) => (
                  <th key={year}>{year}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((metric, index) => (
                <tr key={index}>
                  <td>{metric.method}</td>
                  {years.map((year) => {
                    const value = metric.errors[year];
                    return (
                      <td key={year}>
                        {value !== null && value !== undefined ? (
                          <span className={`${styles.errorValue} ${getErrorClass(value)}`}>
                            {value.toFixed(1)}%
                          </span>
                        ) : (
                          <span className={styles.noData}>—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className={styles.container}>
        <p>Пояснение:</p>
      <ul>
        <li>Для каждого года прогноз сравнивается с фактом</li>
        <li>Для расчёта ошибки используется взвешенная процентная ошибка wMAPE = sum(|Факт - Прогноз|) / sum(|Факт|)</li>
        <li>Цветовая разметка ошибок: 🔴 &gt; 30% | 🟡 15% – 30% | 🟢 &lt; 15%</li>
      </ul>
      </div>
    </div>
  );
}

export const PlanVsFact = memo(PlanVsFactComponent);