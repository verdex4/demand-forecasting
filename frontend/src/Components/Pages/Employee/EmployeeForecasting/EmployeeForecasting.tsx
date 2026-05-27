import { JSX, memo, useState, useEffect } from "react";
import styles from './Styles.module.scss';

import { useSpecialties } from "@/Hooks/useSpecialties";
import { useYearsHorizon } from "@/Hooks/useYearsHorizon";
import { useYearsHistory } from "@/Hooks/useYearsHistory";

import { Button } from "@/Components/UI/Button";
import { useReportGeneration } from "@/Hooks/useReportGeneration";
import { ReportModalWindow } from "@/Components/Widgets/ReportModal";

function EmployeeForecastingComponent(): JSX.Element {
  const {
    specialties,
    loading: loadingSpec,
    error: errorSpec
  } = useSpecialties();

  const {
    yearsHorizon,
    loading: loadingHorizon,
    error: errorHorizon
  } = useYearsHorizon();

  const {
    yearsHistory,
    loading: loadingHistory,
    error: errorHistory
  } = useYearsHistory();

  const {
    isLoading: isReportLoading,
    error: reportError,
    reportUrl,
    generateReport,
    reset: resetReportState
  } = useReportGeneration();

  const [isModalOpen, setIsModalOpen] = useState(false);

  const [specialty, setSpecialty] = useState('');

  const [forecastMethod, setForecastMethod] = useState('');
  const [movingAverageYears, setMovingAverageYears] = useState('');

  const [yearFromHorizon, setYearFromHorizon] = useState('');
  const [yearToHorizon, setYearToHorizon] = useState('');

  const [yearFromHistory, setYearFromHistory] = useState('');
  const [yearToHistory, setYearToHistory] = useState('');

  const isFormValid =
    specialty &&
    forecastMethod &&
    yearFromHorizon &&
    yearToHorizon &&
    yearFromHistory &&
    yearToHistory &&
    (
      forecastMethod !== 'sma' ||
      movingAverageYears
    );

  const handleSubmit = async () => {
    const finalMethod =
      forecastMethod === 'sma' && movingAverageYears
        ? `sma_${movingAverageYears}`
        : forecastMethod;

    const params = {
      specialty,

      horizon: {
        from: yearFromHorizon,
        to: yearToHorizon
      },

      history: {
        from: yearFromHistory,
        to: yearToHistory
      },

      method: finalMethod
    };

    setIsModalOpen(true);

    await generateReport(params);
  };

  const handleReset = () => {
    setSpecialty('');

    setForecastMethod('');
    setMovingAverageYears('');

    setYearFromHistory('');
    setYearFromHorizon('');

    setYearToHistory('');
    setYearToHorizon('');

    resetReportState();

    setIsModalOpen(false);
  };

  const closeModal = () => {
    setIsModalOpen(false);

    resetReportState();
  };

  useEffect(() => {
    if (!yearFromHorizon || !yearToHorizon) return;

    if (Number(yearFromHorizon) > Number(yearToHorizon)) {
      setYearToHorizon(yearFromHorizon);
    }
  }, [yearFromHorizon, yearToHorizon]);

  useEffect(() => {
    if (!yearFromHistory || !yearToHistory) return;

    if (Number(yearFromHistory) > Number(yearToHistory)) {
      setYearToHistory(yearFromHistory);
    }
  }, [yearFromHistory, yearToHistory]);

  if (loadingSpec || loadingHorizon || loadingHistory) {
    return <div>Загрузка...</div>;
  }

  if (errorSpec) {
    return <div>Ошибка: {errorSpec}</div>;
  }

  if (errorHorizon) {
    return <div>Ошибка: {errorHorizon}</div>;
  }

  if (errorHistory) {
    return <div>Ошибка: {errorHistory}</div>;
  }

  return (
    <>
      <div>
        <div className={styles.header}>
          <h2 className={styles.title}>
            Прогноз востребованности специальностей
          </h2>

          <h3 className={styles.subtitle}>
            Параметры прогноза
          </h3>
        </div>

        <div className={styles.container}>
          <div className={styles.input__container}>
            <label htmlFor="specialty">
              Направление подготовки
            </label>

            <select
              name="specialty"
              id="specialty"
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
            >
              <option value="">
                Выберите специальность
              </option>

              {specialties.map((specialtyItem) => (
                <option
                  key={specialtyItem.value}
                  value={specialtyItem.value}
                >
                  {specialtyItem.label}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.input__container}>
            <label htmlFor="forecastMethod">
              Метод прогнозирования
            </label>

            <select
              id="forecastMethod"
              value={forecastMethod}
              onChange={(e) => {
                setForecastMethod(e.target.value);

                if (e.target.value !== 'sma') {
                  setMovingAverageYears('');
                }
              }}
            >
              <option value="">
                Выберите метод
              </option>

              <option value="sma">
                Скользящее среднее
              </option>

              <option value="demographic">
                Демографический метод
              </option>

              <option value="exponential_smoothing">
                Экспоненциальное сглаживание
              </option>
            </select>
          </div>

          {forecastMethod === 'sma' && (
            <div className={styles.input__container}>
              <label htmlFor="movingAverageYears">
                Количество лет
              </label>

              <select
                id="movingAverageYears"
                value={movingAverageYears}
                onChange={(e) =>
                  setMovingAverageYears(e.target.value)
                }
              >
                <option value="">
                  Выберите период
                </option>

                <option value="1">
                  За 1 год
                </option>

                <option value="2">
                  За 2 года
                </option>

                <option value="3">
                  За 3 года
                </option>

                <option value="4">
                  За 4 года
                </option>
              </select>
            </div>
          )}

          <div className={styles.input__container}>
            <label>
              Горизонт прогноза
            </label>

            <div className={styles.years}>
              <select
                name="YearFromHorizon"
                id="YearFromHorizon"
                value={yearFromHorizon}
                onChange={(e) =>
                  setYearFromHorizon(e.target.value)
                }
              >
                <option value="">
                  Год от
                </option>

                {yearsHorizon.map((year) => (
                  <option
                    key={year.value}
                    value={year.value}
                  >
                    {year.label}
                  </option>
                ))}
              </select>

              <span>—</span>

              <select
                name="YearToHorizon"
                id="YearToHorizon"
                value={yearToHorizon}
                onChange={(e) =>
                  setYearToHorizon(e.target.value)
                }
              >
                <option value="">
                  Год до
                </option>

                {yearsHorizon.map((year) => (
                  <option
                    key={year.value}
                    value={year.value}
                  >
                    {year.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.input__container}>
            <label>
              Исторические данные
            </label>

            <div className={styles.years}>
              <select
                name="YearFromHistory"
                id="YearFromHistory"
                value={yearFromHistory}
                onChange={(e) =>
                  setYearFromHistory(e.target.value)
                }
              >
                <option value="">
                  Год от
                </option>

                {yearsHistory.map((year) => (
                  <option
                    key={year.value}
                    value={year.value}
                  >
                    {year.label}
                  </option>
                ))}
              </select>

              <span>—</span>

              <select
                name="YearToHistory"
                id="YearToHistory"
                value={yearToHistory}
                onChange={(e) =>
                  setYearToHistory(e.target.value)
                }
              >
                <option value="">
                  Год до
                </option>

                {yearsHistory.map((year) => (
                  <option
                    key={year.value}
                    value={year.value}
                  >
                    {year.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className={styles.button_container}>
          <Button
            onClick={handleSubmit}
            disabled={!isFormValid}
          >
            Сформировать отчёт
          </Button>

          <Button onClick={handleReset}>
            Сбросить фильтры
          </Button>

          <Button>
            Настройки отчёта
          </Button>
        </div>
      </div>

      <ReportModalWindow
        isOpen={isModalOpen}
        isLoading={isReportLoading}
        error={reportError}
        reportUrl={reportUrl}
        onClose={closeModal}
      />
    </>
  );
}

export const EmployeeForecasting = memo(EmployeeForecastingComponent);