import { useState } from 'react';

type GenerateReportParams = {
  specialty: string;

  history: {
    from: string;
    to: string;
  };

  horizon: {
    from: string;
    to: string;
  };

  method: string;
};

type ApiResponse = {
  success: boolean;
  report_url: string;
};

const API_URL = `${import.meta.env.VITE_API_URL}/api/v1/reports/`;

export function useReportGeneration() {
  const [isLoading, setIsLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [reportUrl, setReportUrl] = useState<string | null>(null);

  const generateReport = async (
    params: GenerateReportParams
  ) => {
    try {
      setIsLoading(true);

      setError(null);

      setReportUrl(null);

      const body = {
        input_specialty: params.specialty,

        history_range: [
          Number(params.history.from),
          Number(params.history.to),
        ],

        forecast_range: [
          Number(params.horizon.from),
          Number(params.horizon.to),
        ],

        method: params.method,
      };

      const response = await fetch(API_URL, {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('Ошибка генерации отчёта');
      }

      const data: ApiResponse = await response.json();

      if (data.success) {
        setReportUrl(data.report_url);
      } else {
        throw new Error('Не удалось создать отчёт');
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Ошибка сервера'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setError(null);

    setReportUrl(null);

    setIsLoading(false);
  };

  return {
    isLoading,
    error,
    reportUrl,
    generateReport,
    reset,
  };
}