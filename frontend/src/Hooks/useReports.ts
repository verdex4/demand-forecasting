import { useEffect, useState } from 'react';

export type Report = {
  id: number;
  specialty_id: number;
  specialty_full_name: string;
  method: string;
  start_year: number;
  current_year: number;
  end_year: number;
  url: string;
};

const API_URL = `${import.meta.env.VITE_API_URL}/api/v1/reports`;

export function useReports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const response = await fetch(API_URL);

        if (!response.ok) {
          throw new Error(`Ошибка ${response.status}`);
        }

        const data = await response.json();

        setReports(data);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Ошибка загрузки отчётов'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  return {
    reports,
    loading,
    error,
  };
}