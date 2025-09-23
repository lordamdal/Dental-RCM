import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import AppShell from './shell/AppShell'
import CaseView from './views/CaseView'
import './index.css'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell/>,
    children: [
      { index: true, element: <div className="h-full grid place-items-center text-gray-500">Select or create a case</div> },
      { path: '/cases/:caseId', element: <CaseView/> },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
