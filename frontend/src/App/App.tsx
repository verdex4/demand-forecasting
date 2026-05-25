import { EmployeePage } from '@/Components/Layouts/EmployeeLayout';
import { EmployeeForecasting } from '@/Components/Pages/Employee/EmployeeForecasting';
import { Login } from '@/Components/Pages/Login';
import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import '../Styles/index.scss';
import './Styles.scss';

function AppComponent() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login/>} />
        <Route path="/applicant" element={<div>Панель сотрудника</div>} />
        <Route path="/employee" element={<EmployeePage/>} >
          <Route index element={<Navigate to="forecasting" replace />} />
          <Route path="forecasting" element={<EmployeeForecasting/>} />
          <Route path="statistics" element={<div>Статистика для сотрудника</div>} />
          <Route path="reports" element={<div>Статистика для сотрудника</div>} />
        </Route>
        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export const App = AppComponent;
