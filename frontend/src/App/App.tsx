import { EmployeePage } from '@/Components/Layouts/EmployeeLayout';
import { EmployeeForecasting } from '@/Components/Pages/Employee/EmployeeForecasting';
import { Login } from '@/Components/Pages/Login';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import '../Styles/index.scss';
import './Styles.scss';
import { EmployeeHelp } from '@/Components/Pages/Employee/EmployeeHelp';

function AppComponent() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login/>} />
        <Route path="/employee" element={<EmployeePage/>} >
          <Route index element={<Navigate to="forecasting" replace />} />
          <Route path="forecasting" element={<EmployeeForecasting/>} />
          <Route path="help" element={<EmployeeHelp/>} />
        </Route>
        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export const App = AppComponent;
