import { JSX, memo, useState, useEffect, useMemo, useRef } from "react";
import styles from './Styles.module.scss';

import { useSpecialties } from "@/Hooks/useSpecialties";
import { useYearsHorizon } from "@/Hooks/useYearsHorizon";
import { useYearsHistoryFrom } from "@/Hooks/useYearsHistoryFrom";
import { useYearsHistoryTo } from "@/Hooks/useYearsHistoryTo";

import { Button } from "@/Components/UI/Button";
import { useReportGeneration } from "@/Hooks/useReportGeneration";
import type { GenerateReportParams } from '@/Hooks/useReportGeneration'; 
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

  // Ввод КЦП и платных мест
  const [kcpMode, setKcpMode] = useState<'manual' | 'percentage' | null>(null);
  const [paidMode, setPaidMode] = useState<'manual' | 'percentage' | null>(null);
  const [kcpManualValues, setKcpManualValues] = useState<Record<string, string>>({});
  const [paidManualValues, setPaidManualValues] = useState<Record<string, string>>({});
  const [kcpGrowthPct, setKcpGrowthPct] = useState('');
  const [paidGrowthPct, setPaidGrowthPct] = useState('');

  // Начальный год прогноза вычисляется автоматически и не хранится в стейте
  const yearFromHorizon = useMemo(() => {
    if (!yearToHistory) return '';
    const nextYearStr = String(Number(yearToHistory) + 1);
    const isAvailable = yearsHorizon.some((y) => y.value === nextYearStr);
    return isAvailable ? nextYearStr : '';
  }, [yearToHistory, yearsHorizon]);

  // Получаем список лет прогноза для отображения полей
  const forecastYears = useMemo(() => {
    if (!yearFromHorizon || !yearToHorizon) return [];
    const from = Number(yearFromHorizon);
    const to = Number(yearToHorizon);
    const years: string[] = [];
    for (let year = from; year <= to; year++) {
      years.push(String(year));
    }
    return years;
  }, [yearFromHorizon, yearToHorizon]);

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

  // Сброс значений КЦП и платных мест при изменении диапазона прогноза
  useEffect(() => {
    setKcpManualValues({});
    setPaidManualValues({});
    setKcpGrowthPct('');
    setPaidGrowthPct('');
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
      forecastMethod !== 'Скользящее среднее' ||
      movingAverageYears
    );

    const handleSubmit = async () => {
      let finalMethod = forecastMethod;

      if (forecastMethod === 'Скользящее среднее' && movingAverageYears) {
        const window = Number(movingAverageYears);
        const remainder100 = window % 100;
        const remainder10 = window % 10;

        if (remainder100 >= 11 && remainder100 <= 14) {
          finalMethod = `Скользящее среднее за ${window} лет`;
        } else if (remainder10 === 1) {
          finalMethod = `Скользящее среднее за ${window} год`;
        } else if (remainder10 >= 2 && remainder10 <= 4) {
          finalMethod = `Скользящее среднее за ${window} года`;
        } else {
          finalMethod = `Скользящее среднее за ${window} лет`;
        }
      }

      const params : GenerateReportParams = {
        specialty,
        horizon: {
          from: yearFromHorizon,
          to: yearToHorizon
        },
        history: {
          from: yearFromHistory,
          to: yearToHistory
        },
        method: finalMethod,
      };

      // Добавляем данные КЦП
      if (kcpMode === 'manual') {
        const kcpManual: Record<string, number> = {};
        forecastYears.forEach(year => {
          const value = kcpManualValues[year];
          if (value !== undefined && value !== null && String(value).trim() !== '') {
            kcpManual[year] = Number(value);
          }
        });
        params.kcpManual = kcpManual;
      } else if (kcpMode === 'percentage') {
        params.kcpGrowthPct = kcpGrowthPct ? Number(kcpGrowthPct) : undefined;
      }

      // Добавляем данные платных
      if (paidMode === 'manual') {
        const paidManual: Record<string, number> = {};
        forecastYears.forEach(year => {
          const value = paidManualValues[year];
          if (value !== undefined && value !== null && String(value).trim() !== '') {
            paidManual[year] = Number(value);
          }
        });
        params.paidManual = paidManual;
      } else if (paidMode === 'percentage') {
        params.paidGrowthPct = paidGrowthPct ? Number(paidGrowthPct) : undefined;
      }

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

  const handleKcpManualChange = (year: string, value: string) => {
    setKcpManualValues(prev => ({
      ...prev,
      [year]: value
    }));
  };

  const handlePaidManualChange = (year: string, value: string) => {
    setPaidManualValues(prev => ({
      ...prev,
      [year]: value
    }));
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

                if (e.target.value !== 'Сколязящее среднее') {
                  setMovingAverageYears('');
                }
              }}
            >
              <option value="">
                Выберите метод
              </option>

              <option value="Последнее значение">
                Последнее значение
              </option>

              <option value="Скользящее среднее">
                Скользящее среднее
              </option>

              <option value="Демографический метод">
                Демографический метод
              </option>

              <option value="Экспоненциальное сглаживание">
                Экспоненциальное сглаживание
              </option>
            </select>
          </div>

          {forecastMethod === 'Скользящее среднее' && (
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

                <option value="2">
                  За 2 года
                </option>

                <option value="3">
                  За 3 года
                </option>

                <option value="4">
                  За 4 года
                </option>

                <option value="5">
                  За 5 лет
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

          {/* КЦП и платные места */}
          {yearToHorizon && (
            <>
              {/* КЦП */}
              <div className={styles.input__container}>
                <label>
                  КЦП (Контрольные цифры приёма)
                </label>
                
                <div className={styles.mode_selection}>
                  <button
                    type="button"
                    className={`${styles.mode_button} ${kcpMode === 'manual' ? styles.active : ''}`}
                    onClick={() => setKcpMode(kcpMode === 'manual' ? null : 'manual')}
                  >
                    Вручную
                  </button>
                  <button
                    type="button"
                    className={`${styles.mode_button} ${kcpMode === 'percentage' ? styles.active : ''}`}
                    onClick={() => setKcpMode(kcpMode === 'percentage' ? null : 'percentage')}
                  >
                    В процентах прироста
                  </button>
                </div>

                {kcpMode === 'manual' && forecastYears.length > 0 && (
                  <div className={styles.manual_inputs}>
                    {forecastYears.map((year) => (
                      <div key={year} className={styles.manual_row}>
                        <div className={styles.manual_year}>{year}</div>
                        <input
                          type="number"
                          min="0"
                          placeholder="Введите значение"
                          value={kcpManualValues[year] || ''}
                          onChange={(e) => handleKcpManualChange(year, e.target.value)}
                          className={styles.manual_input}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {kcpMode === 'percentage' && (
                  <div className={styles.percentage_input}>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="Введите процент прироста"
                      value={kcpGrowthPct}
                      onChange={(e) => setKcpGrowthPct(e.target.value)}
                      className={styles.input_field}
                    />
                    <span className={styles.percent_sign}>%</span>
                  </div>
                )}
              </div>

              {/* Платные места */}
              <div className={styles.input__container}>
                <label>
                  Платные места
                </label>
                
                <div className={styles.mode_selection}>
                  <button
                    type="button"
                    className={`${styles.mode_button} ${paidMode === 'manual' ? styles.active : ''}`}
                    onClick={() => setPaidMode(paidMode === 'manual' ? null : 'manual')}
                  >
                    Вручную
                  </button>
                  <button
                    type="button"
                    className={`${styles.mode_button} ${paidMode === 'percentage' ? styles.active : ''}`}
                    onClick={() => setPaidMode(paidMode === 'percentage' ? null : 'percentage')}
                  >
                    В процентах прироста
                  </button>
                </div>

                {paidMode === 'manual' && forecastYears.length > 0 && (
                  <div className={styles.manual_inputs}>
                    {forecastYears.map((year) => (
                      <div key={year} className={styles.manual_row}>
                        <div className={styles.manual_year}>{year}</div>
                        <input
                          type="number"
                          min="0"
                          placeholder="Введите значение"
                          value={paidManualValues[year] || ''}
                          onChange={(e) => handlePaidManualChange(year, e.target.value)}
                          className={styles.manual_input}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {paidMode === 'percentage' && (
                  <div className={styles.percentage_input}>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="Введите процент прироста"
                      value={paidGrowthPct}
                      onChange={(e) => setPaidGrowthPct(e.target.value)}
                      className={styles.input_field}
                    />
                    <span className={styles.percent_sign}>%</span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className={styles.button_container}>
          <Button
            onClick={handleSubmit}
            disabled={!isFormValid}
          >
            Сформировать отчёт
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