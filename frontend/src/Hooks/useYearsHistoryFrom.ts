import { useState, useEffect } from 'react';

export type Year = {
  value: string;
  label: string;
};

const START_YEAR = 2019;
const END_YEAR = 2022;

export function useYearsHistoryFrom() {
  const [years, setYears] = useState<Year[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchYears = async () => {
      try {
        await new Promise(resolve => setTimeout(resolve, 300));
        const years: Year[] = [];
        for (let year = START_YEAR; year <= END_YEAR; year++) {
          years.push({ value: year.toString(), label: year.toString() });
        }
        setYears(years);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
      } finally {
        setLoading(false);
      }
    };

    fetchYears();
  }, []);

  return { years, loading, error };
}