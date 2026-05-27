import { useEffect, useState } from 'react';

type Specialty = {
  value: string;
  label: string;
};

type ApiSpecialty = {
  code: string;
  name: string;
  id: number;
};

const API_URL = `${import.meta.env.VITE_API_URL}/api/v1/specialties/short`;

export function useSpecialties() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSpecialties = async () => {
      try {
        const response = await fetch(API_URL);

        if (!response.ok) {
          throw new Error(`Ошибка сервера: ${response.status}`);
        }

        const data: ApiSpecialty[] = await response.json();

        const mappedSpecialties = data
          .filter((spec) => spec.code && spec.code !== 'nan')
          .map((spec) => ({
            value: spec.code,
            label: `${spec.code} ${spec.name}`,
          }));

        setSpecialties(mappedSpecialties);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Ошибка загрузки специальностей'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchSpecialties();
  }, []);

  return {
    specialties,
    loading,
    error,
  };
}