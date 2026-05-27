import { Header } from "@/Components/Widgets/Header";
import { LeftLinks } from "@/Components/Widgets/LeftLinks/LeftLinks";
import { JSX, memo } from "react";
import { Outlet } from "react-router";
import styles from './Styles.module.scss';

const applicantLinks = [
  {name: 'Прогнозирование', link: '/applicant/forecasting'},
  //{name: 'Специальности', link: '/employee/specialties'},
  //{name: 'Статистика ЕГЭ', link: '/employee/statistics'},
  //{name: 'Отчёты', link: '/employee/reports'}
];

function ApplicantLayout(): JSX.Element {
  return (
    <div>
      <Header/>
      <LeftLinks links={applicantLinks}/>
      <main>
        <Outlet/>
      </main>
    </div>
  );
}

export const ApplicantPage = memo(ApplicantLayout);