import { useState, useEffect } from 'react';

type Year = {
  value: string;
  label: string;
};

const START_YEAR = 2020;
const END_YEAR = 2030;

const generateYears = (): Year[] => {
  const years: Year[] = [];
  for (let year = START_YEAR; year <= END_YEAR; year++) {
    years.push({ value: year.toString(), label: year.toString() });
  }
  return years;
};

const mockYears: Year[] = generateYears();

export function useYearsHorizon() {
  const [yearsHorizon, setYears] = useState<Year[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchYears = async () => {
      try {
        setYears(mockYears);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
      } finally {
        setLoading(false);
      }
    };

    fetchYears();
  }, []);

  return { yearsHorizon, loading, error };
}