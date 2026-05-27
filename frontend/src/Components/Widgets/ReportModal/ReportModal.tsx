import { JSX, memo } from "react";
import styles from './Styles.module.scss';

interface ReportModalProps {
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;
  reportUrl: string | null;
  onClose: () => void;
}

function ReportModal({
  isOpen,
  isLoading,
  error,
  reportUrl,
  onClose
}: ReportModalProps): JSX.Element {
  if (!isOpen) return <div />; // Исправлено: возвращаем пустой div

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <button className={styles.closeButton} onClick={onClose}>
          ×
        </button>
        <h3>Статус отчёта</h3>
        {isLoading ? (
          <div className={styles.loadingState}>
            <div className={styles.spinner}></div>
            <p>Отчёт готовится, пожалуйста, подождите...</p>
          </div>
        ) : error ? (
          <div className={styles.errorState}>
            <p>{error}</p>
            <button onClick={onClose} className={styles.retryButton}>
              Попробовать ещё раз
            </button>
          </div>
        ) : reportUrl ? (
          <div className={styles.successState}>
            <p>Ваш отчёт готов по ссылке:</p>
            <a
              href={reportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.reportLink}
            >
              {reportUrl}
            </a>
            <button onClick={onClose} className={styles.closeModalButton}>
              Закрыть
            </button>
          </div>
        ) : (
          <div className={styles.errorState}>
            <p>Не удалось получить ссылку на отчёт</p>
            <button onClick={onClose} className={styles.closeModalButton}>
              Закрыть
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export const ReportModalWindow = memo(ReportModal);
