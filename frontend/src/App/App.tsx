import { EmployeePage } from '@/Components/Layouts/EmployeeLayout';
import { EmployeeForecasting } from '@/Components/Pages/Employee/EmployeeForecasting';
import { Login } from '@/Components/Pages/Login';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import '../Styles/index.scss';
import './Styles.scss';
import { EmployeeHelp } from '@/Components/Pages/Employee/EmployeeHelp';
import { EmployeeReports } from '@/Components/Pages/Employee/EmployeeReports';
import {PlanVsFact} from '@/Components/Pages/Employee/EmployeePlanVsFact';

function AppComponent() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login/>} />
        <Route path="/employee" element={<EmployeePage/>} >
          <Route index element={<Navigate to="forecasting" replace />} />
          <Route path="forecasting" element={<EmployeeForecasting/>} />
          <Route path="help" element={<EmployeeHelp/>} />
          <Route path="reports" element={<EmployeeReports/>} />
          <Route path="plan-vs-fact" element={<PlanVsFact />} />
        </Route>
        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export const App = AppComponent;
