import { JSX, memo } from 'react';
import styles from './Styles.module.scss';

function EmployeeHelpComponent(): JSX.Element {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          Справка
        </h1>

        <p className={styles.subtitle}>
          Описание логики работы системы прогнозирования
        </p>
      </div>

      <div className={styles.container}>
        <section>
          <h2>Прогноз базовых показателей за каждый год</h2>

          <p>
            Система прогнозирует три базовых показателя:
          </p>

          <ul>
            <li>Количество заявлений.</li>
            <li>КЦП (контрольные цифры приёма).</li>
            <li>Количество зачисленных.</li>
          </ul>

          <p>
            Для расчёта используются методы прогнозирования:
          </p>

          <ul>
            <li>Скользящее среднее за n лет — показатели за текущий год равны среднему за предыдущие n лет.</li>
            <li>Демографический метод — показатели за текущий год строго зависят от измения рождаемости 18 лет назад (т.к. большинство поступает в 18 лет).</li>
            <li>Экспоненциальное сглаживание — текущие показатели определяются прошлыми данными, где наибольший вес имеют последние годы.</li>
          </ul>

          <p>
            Формулы расчёта:
          </p>
          <ul>
            <li>
              <div className={styles.formula}>
                Ŷ<sub>t</sub> = average(Y<sub>t-1</sub>, Y<sub>t-2</sub>, ..., Y<sub>t-n</sub>)
              </div>
            </li>

            <li>
              <div className={styles.formula}>
                Ŷ<sub>t</sub> = Y<sub>t-1</sub> × (1 + изменение_рождаемости)
              </div>
            </li>

            <li>
              <div className={styles.formula}>
                Ŷ<sub>t</sub> = α × Y<sub>t-1</sub> + (1 - α) × Ŷ<sub>t-1</sub>
              </div>
            </li>
          </ul>
        </section>

        <section>
          <h2>Промежуточные показатели</h2>

          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Показатель</th>
                  <th>Что отражает</th>
                  <th>Как вычисляется</th>
                </tr>
              </thead>

              <tbody>
                <tr>
                  <td>D<sub>1</sub></td>
                  <td>Коммерческий интерес</td>
                  <td>Равен доле внебюджетников</td>
                </tr>

                <tr>
                  <td>D<sub>2</sub></td>
                  <td>Показатель заявлений</td>
                  <td>Разница с медианой и темп прироста</td>
                </tr>

                <tr>
                  <td>D<sub>3</sub></td>
                  <td>Показатель конкурса</td>
                  <td>Разница с медианой и темп прироста</td>
                </tr>

                <tr>
                  <td>D<sub>4</sub></td>
                  <td>Показатель КЦП</td>
                  <td>Разница с медианой и темп прироста</td>
                </tr>

                <tr>
                  <td>D<sub>5</sub></td>
                  <td>Штраф за недобор</td>
                  <td>Доля незачисленных относительно КЦП</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p>Весовые коэффициенты по умолчанию</p>

          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Вес</th>
                  <th>Значение</th>
                  <th>Влияет на</th>
                </tr>
              </thead>

              <tbody>
                <tr>
                  <td>w<sub>1</sub></td>
                  <td>0.25</td>
                  <td>Коммерческий интерес (D<sub>1</sub>)</td>
                </tr>

                <tr>
                  <td>w<sub>2</sub></td>
                  <td>0.25</td>
                  <td>Показатель заявлений (D<sub>2</sub>)</td>
                </tr>

                <tr>
                  <td>w<sub>3</sub></td>
                  <td>0.40</td>
                  <td>Показатель конкурса (D<sub>3</sub>)</td>
                </tr>

                <tr>
                  <td>w<sub>4</sub></td>
                  <td>0.10</td>
                  <td>Показатель КЦП (D<sub>4</sub>)</td>
                </tr>

                <tr>
                  <td>w<sub>5</sub></td>
                  <td>-10</td>
                  <td>Штраф за недобор (D<sub>5</sub>)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2>Итоговый показатель востребованности</h2>

          <div className={styles.formula}>
            D = (w<sub>1</sub>·D<sub>1</sub> + w<sub>2</sub>·D<sub>2</sub> + w<sub>3</sub>·D<sub>3</sub> + w<sub>4</sub>·D<sub>4</sub>) × exp(w<sub>5</sub>·D<sub>5</sub>)
          </div>

          <p>
            Итоговый показатель находится в диапазоне от 0 до 1 и отражает
            общую востребованность направления подготовки.
          </p>
        </section>

        <section>
          <h2>Интерпретация результата</h2>

          <ul>
            <li><strong>Очень высокий</strong> — специальность входит в топ-25% лучших.</li>
            <li><strong>Высокий</strong> — от 25% до 50% лучших.</li>
            <li><strong>Средний</strong> — от 50% до 75%.</li>
            <li><strong>Низкий</strong> — худшие 25% направлений.</li>
          </ul>
          
          <p>
            Примечание: стабильность востребованности считается на основе стандартного отклонения 
            итогового показателя D за всё время (история + прогноз) и ранжируется аналогичным образом от лучших к худшим.
          </p>
        </section>

        <section>
          <h2>Ограничения текущей версии</h2>

          <ul>
            <li>
              Используется только внутренняя статистика университета.
            </li>

            <li>
              Ручная настройка весов пока не поддерживается.
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}

export const EmployeeHelp = memo(EmployeeHelpComponent);