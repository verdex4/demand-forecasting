import { Header } from "@/Components/Widgets/Header";
import { LeftLinks } from "@/Components/Widgets/LeftLinks/LeftLinks";
import { JSX, memo } from "react";
import { Outlet } from "react-router";
import styles from './Styles.module.scss';

const employeeLinks = [
  {name: 'Прогнозирование', link: '/employee/forecasting'},
  {name: 'Справка', link: '/employee/help'},
  {name: 'Отчёты', link: '/employee/reports'}
];

function EmployeeLayout(): JSX.Element {
  return (
    <div className={styles.container}>
      <aside className={styles.sidebar}>
        <Header role="Сотрудник вуза"/>
        <LeftLinks links={employeeLinks}/>
      </aside>
      <main className={styles.content}>
        <Outlet/>
      </main>
    </div>
  );
}

export const EmployeePage = memo(EmployeeLayout);