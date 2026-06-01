import { useState, useEffect } from 'react';

export type Year = {
  value: string;
  label: string;
};

const START_YEAR = 2019;
const END_YEAR = 2023;

const generateYears = (): Year[] => {
  const years: Year[] = [];
  for (let year = START_YEAR; year <= END_YEAR; year++) {
    years.push({ value: year.toString(), label: year.toString() });
  }
  return years;
};

const mockYears: Year[] = generateYears();

export function useYearsHistory() {
  const [yearsHistory, setYears] = useState<Year[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchYears = async () => {
      try {
        await new Promise(resolve => setTimeout(resolve, 300));
        setYears(mockYears);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
      } finally {
        setLoading(false);
      }
    };

    fetchYears();
  }, []);

  return { yearsHistory, loading, error };
}