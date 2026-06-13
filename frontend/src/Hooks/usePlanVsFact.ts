import { useState, useCallback } from 'react';

export interface MetricData {
  name: string;
  errors: Record<number, number | null>;
}

export interface MethodData {
  method: string;
  metrics: MetricData[];
}

const API_URL = `${import.meta.env.VITE_API_URL}/api/v1/model/errors`;

export const usePlanVsFact = () => {
  const [data, setData] = useState<MethodData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchErrors = useCallback(async () => {
    setLoading(true);
    setError(null);
    setData([]);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Ошибка при загрузке данных точности модели');
      }

      const result: MethodData[] = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла неизвестная ошибка');
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, fetchErrors };
};

export default usePlanVsFact;