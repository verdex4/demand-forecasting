import { useState, useEffect } from 'react';

type Year = {
  value: string;
  label: string;
};

const generateYears = (): Year[] => {
  const currentYear = new Date().getFullYear();
  const years: Year[] = [];
  
  for (let year = 2020; year <= currentYear + 10; year++) {
    years.push({ 
      value: year.toString(), 
      label: year.toString() 
    });
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