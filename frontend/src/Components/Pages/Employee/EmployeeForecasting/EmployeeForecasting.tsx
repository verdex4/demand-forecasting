import { JSX, memo, useState, useEffect, useMemo, useRef } from "react";
import styles from './Styles.module.scss';

import { useSpecialties } from "@/Hooks/useSpecialties";
import { useYearsHorizon } from "@/Hooks/useYearsHorizon";
import { useYearsHistoryFrom } from "@/Hooks/useYearsHistoryFrom";
import { useYearsHistoryTo } from "@/Hooks/useYearsHistoryTo";

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
    years: yearsHistoryFrom,
    loading: loadingHistoryFrom,
    error: errorHistoryFrom
  } = useYearsHistoryFrom();

  const {
    years: yearsHistoryTo,
    loading: loadingHistoryTo,
    error: errorHistoryTo
  } = useYearsHistoryTo();

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

  const [yearToHorizon, setYearToHorizon] = useState('');

  const [yearFromHistory, setYearFromHistory] = useState('');
  const [yearToHistory, setYearToHistory] = useState('');

  // Состояние для отображения предупреждения о невозможности редактирования
  const [showReadonlyWarning, setShowReadonlyWarning] = useState(false);
  const warningRef = useRef<HTMLDivElement>(null);

  // Начальный год прогноза вычисляется автоматически и не хранится в стейте
  const yearFromHorizon = useMemo(() => {
    if (!yearToHistory) return '';
    const nextYearStr = String(Number(yearToHistory) + 1);
    const isAvailable = yearsHorizon.some((y) => y.value === nextYearStr);
    return isAvailable ? nextYearStr : '';
  }, [yearToHistory, yearsHorizon]);

  const yearsHistoryToOptions = useMemo(() => {
    if (!yearFromHistory) return yearsHistoryTo;
    const fromNum = Number(yearFromHistory);
    return yearsHistoryTo.filter((y) => Number(y.value) > fromNum);
  }, [yearFromHistory, yearsHistoryTo]);

  const yearsHorizonToOptions = useMemo(() => {
    let options = yearsHorizon;
    
    // Ограничение по истории: только года > yearToHistory
    if (yearToHistory) {
      const historyEnd = Number(yearToHistory);
      options = options.filter((y) => Number(y.value) > historyEnd);
    }
    
    // Ограничение по начальному году прогноза: только года >= yearFromHorizon
    if (yearFromHorizon) {
      const fromNum = Number(yearFromHorizon);
      options = options.filter((y) => Number(y.value) >= fromNum);
    }
    
    return options;
  }, [yearFromHorizon, yearToHistory, yearsHorizon]);

  useEffect(() => {
    if (!yearFromHistory) {
      setYearToHistory('');
      return;
    }
    if (yearToHistory && Number(yearToHistory) < Number(yearFromHistory)) {
      setYearToHistory('');
    }
  }, [yearFromHistory, yearToHistory]);

  useEffect(() => {
    if (!yearFromHorizon) {
      setYearToHorizon('');
      return;
    }
    if (yearToHorizon && Number(yearToHorizon) < Number(yearFromHorizon)) {
      setYearToHorizon('');
    }
  }, [yearFromHorizon, yearToHorizon]);

  // Скрываем предупреждение при клике в любое другое место экрана
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        warningRef.current &&
        !warningRef.current.contains(event.target as Node)
      ) {
        setShowReadonlyWarning(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

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
    setYearToHistory('');
    setYearToHorizon('');

    resetReportState();

    setIsModalOpen(false);
  };

  const closeModal = () => {
    setIsModalOpen(false);

    resetReportState();
  };

  if (loadingSpec || loadingHorizon || loadingHistoryFrom || loadingHistoryTo) {
    return <div>Загрузка...</div>;
  }

  if (errorSpec) {
    return <div>Ошибка: {errorSpec}</div>;
  }

  if (errorHorizon) {
    return <div>Ошибка: {errorHorizon}</div>;
  }

  if (errorHistoryFrom) {
    return <div>Ошибка: {errorHistoryFrom}</div>;
  }

  if (errorHistoryTo) {
    return <div>Ошибка: {errorHistoryTo}</div>;
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

          {/* --- Исторические данные ------------------------------------ */}
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
                  Начальный год
                </option>

                {yearsHistoryFrom.map((year) => (
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
                disabled={!yearFromHistory}
              >
                <option value="">
                  {yearFromHistory ? 'Конечный год' : 'Сначала выберите начальный год'}
                </option>

                {yearsHistoryToOptions.map((year) => (
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

          {/* Горизонт прогноза */}
          <div className={styles.input__container}>
            <label>
              Горизонт прогноза
            </label>

            <div className={styles.years} style={{ position: 'relative' }}>
              
              <div
                ref={warningRef}
                onClick={() => setShowReadonlyWarning(true)}
                style={{
                  padding: '0 16px',
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  color: yearFromHorizon ? '#fff' : 'rgba(255, 255, 255)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '8px',
                  cursor: 'help',
                  minHeight: '48px',
                  display: 'flex',
                  alignItems: 'center',
                  userSelect: 'none',
                  fontSize: '16px',
                  flex: 1,
                  boxSizing: 'border-box',
                  opacity: yearFromHorizon ? 1 : 0.7
                }}
              >
                {yearFromHorizon || 'Сначала заполните исторические данные'}
              </div>

              {showReadonlyWarning && (
                <div className={styles.readonly_warning}>
                  ⚠️ Данное поле заполняется автоматически и не может быть изменено
                </div>
              )}

              <span>—</span>

              <select
                name="YearToHorizon"
                id="YearToHorizon"
                value={yearToHorizon}
                onChange={(e) =>
                  setYearToHorizon(e.target.value)
                }
                disabled={!yearFromHorizon}
              >
                <option value="">
                  {yearFromHorizon ? 'Конечный год' : 'Сначала заполните исторические данные'}
                </option>

                {yearsHorizonToOptions.map((year) => (
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