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
          Описание логики работы системы прогнозирования востребованности специальностей.
        </p>
      </div>

      <div className={styles.container}>
        <section>
          <h2>Прогноз базовых показателей</h2>

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
            <li>Скользящее среднее.</li>
            <li>Демографический метод.</li>
            <li>Экспоненциальное сглаживание.</li>
          </ul>

          <div className={styles.formula}>
            Ŷₜ = average(Yₜ₋₁ ... Yₜ₋ₙ)
          </div>

          <div className={styles.formula}>
            Ŷₜ = Yₜ₋₁ × (1 + изменение рождаемости)
          </div>

          <div className={styles.formula}>
            Ŷₜ = α × Yₜ₋₁ + (1 - α) × Ŷₜ₋₁
          </div>
        </section>

        <section>
          <h2>Промежуточные показатели</h2>

          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Показатель</th>
                  <th>Описание</th>
                </tr>
              </thead>

              <tbody>
                <tr>
                  <td>D₁</td>
                  <td>Коммерческий интерес</td>
                </tr>

                <tr>
                  <td>D₂</td>
                  <td>Поток заявлений и динамика</td>
                </tr>

                <tr>
                  <td>D₃</td>
                  <td>Конкурс на направление</td>
                </tr>

                <tr>
                  <td>D₄</td>
                  <td>Доля КЦП</td>
                </tr>

                <tr>
                  <td>D₅</td>
                  <td>Штраф за недобор</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2>Итоговый показатель востребованности</h2>

          <div className={styles.formula}>
            D = (w₁·D₁ + w₂·D₂ + w₃·D₃ + w₄·D₄) × exp(w₅·D₅)
          </div>

          <p>
            Итоговый показатель находится в диапазоне от 0 до 1 и отражает
            общую востребованность направления подготовки.
          </p>
        </section>

        <section>
          <h2>Весовые коэффициенты</h2>

          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Вес</th>
                  <th>Значение</th>
                  <th>Назначение</th>
                </tr>
              </thead>

              <tbody>
                <tr>
                  <td>w₁</td>
                  <td>0.25</td>
                  <td>Коммерческий интерес</td>
                </tr>

                <tr>
                  <td>w₂</td>
                  <td>0.25</td>
                  <td>Поток заявлений</td>
                </tr>

                <tr>
                  <td>w₃</td>
                  <td>0.40</td>
                  <td>Конкурс</td>
                </tr>

                <tr>
                  <td>w₄</td>
                  <td>0.10</td>
                  <td>КЦП</td>
                </tr>

                <tr>
                  <td>w₅</td>
                  <td>-10</td>
                  <td>Штраф за недобор</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2>Интерпретация результата</h2>

          <ul>
            <li><strong>Очень высокий</strong> — входит в топ-25% лучших.</li>
            <li><strong>Высокий</strong> — от 25% до 50% лучших.</li>
            <li><strong>Средний</strong> — от 50% до 75%.</li>
            <li><strong>Низкий</strong> — последние 25% направлений.</li>
          </ul>
        </section>

        <section>
          <h2>Ограничения</h2>

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