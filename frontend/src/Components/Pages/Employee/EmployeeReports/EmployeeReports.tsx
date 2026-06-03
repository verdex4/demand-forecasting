import { JSX, memo } from 'react';
import styles from './Styles.module.scss';
import { useReports } from '@/Hooks/useReports';

function EmployeeReportsComponent(): JSX.Element {
  const {
    reports,
    loading,
    error,
  } = useReports();

  if (loading) {
    return <div>Загрузка...</div>;
  }

  if (error) {
    return <div>Ошибка: {error}</div>;
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          Отчёты
        </h1>

        <p className={styles.subtitle}>
          История сформированных отчётов
        </p>
      </div>

      <div className={styles.container}>
        {reports.length === 0 ? (
          <div className={styles.empty}>
            У вас ещё нет отчётов
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Специальность</th>
                  <th>Метод</th>
                  <th>Исторические данные</th>
                  <th>Горизонт прогноза</th>
                  <th>Отчёт</th>
                </tr>
              </thead>

              <tbody>
                {reports.map((report) => (
                  <tr key={report.id}>
                    <td>
                      {report.specialty_full_name}
                    </td>

                    <td>
                      {report.method}
                    </td>

                    <td>
                      {report.start_year} — {report.current_year}
                    </td>

                    <td>
                      {report.current_year} — {report.end_year}
                    </td>

                    <td>
                      <a
                        href={report.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Открыть
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export const EmployeeReports = memo(EmployeeReportsComponent);