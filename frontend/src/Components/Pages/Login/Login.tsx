import styles from './Styles.module.scss';
import { JSX, memo, useState } from 'react';
import { Button } from '../../UI/Button';
import { useNavigate } from 'react-router';

function LoginComponent(): JSX.Element {
  const [role, setRole] = useState<'employee' | 'applicant' | null>(null);

  const navigate = useNavigate();

  const handleContinue = () => {
    if (role === 'employee') {
      navigate('/employee');
    } else if (role === 'applicant') {
      navigate('/applicant');
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <h2 className={styles.title}>
          Аналитика специальностей
        </h2>

        <h3 className={styles.subtitle}>
          Выберите роль для продолжения
        </h3>

        <div className={styles.buttons}>
          <Button
            color={role === 'employee' ? 'blue' : 'secondary'}
            onClick={() => setRole('employee')}
            fullWidth
          >
            Сотрудник вуза
          </Button>

          <Button
            color={role === 'applicant' ? 'blue' : 'secondary'}
            onClick={() => setRole('applicant')}
            fullWidth
          >
            Абитуриент
          </Button>
        </div>

        <Button
          onClick={handleContinue}
          disabled={!role}
          fullWidth
        >
          Продолжить
        </Button>
      </div>
    </div>
  );
}

export const Login = memo(LoginComponent);