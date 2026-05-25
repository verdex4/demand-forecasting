import { Button } from "@/Components/UI/Button";
import { JSX, memo } from "react";
import { useNavigate } from "react-router";
import styles from './Styles.module.scss'

interface HeaderProps {
  role?: string;
}

function HeaderComponent({role}: HeaderProps): JSX.Element {
  const navigate = useNavigate();
  const handleClick = () => {
    navigate('/login');
  }

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <h1 className={styles.title}>
          UniAnalitics
        </h1>

        {role && (
          <h2 className={styles.role}>
            {role}
          </h2>
        )}

        <Button onClick={handleClick}>
          Выйти
        </Button>
      </div>
    </header>
  )
}

export const Header = memo(HeaderComponent);