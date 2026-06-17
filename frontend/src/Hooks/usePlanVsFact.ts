import { useState, useEffect } from 'react';

export interface Metric {
  method: string;
  errors: Record<number, number | null>;
}

export type MetricsResponse = Metric[];

export function usePlanVsFact() {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchErrors = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(
          `${import.meta.env.VITE_API_URL}/api/v1/model/errors`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Ошибка загрузки данных: ${response.status}`);
        }

        const result: MetricsResponse = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
      } finally {
        setLoading(false);
      }
    };

    fetchErrors();
  }, []);

  return { data, loading, error };
}