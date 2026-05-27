import { memo } from "react";
import styles from './LeftLinks.module.scss';
import { Link, useLocation } from 'react-router';

type LeftLinksComponentProps = {
  links: { name: string; link: string }[];
};

function LeftLinksComponent({links}: LeftLinksComponentProps) {
  const location = useLocation();

  return (
    <div>
      <div className={styles.container}>
        {links.map((link, index) => (
          <Link 
            to={link.link} 
            key={index}
            className={`${styles.link} ${location.pathname === link.link ? styles.active : ''}`}
          >
            {link.name}
          </Link>
        ))}
      </div>
    </div>
  );
}

export const LeftLinks = memo(LeftLinksComponent);