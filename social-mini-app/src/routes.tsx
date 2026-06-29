import { createBrowserRouter } from "react-router-dom";
import { Layout } from "./navigation/Layout";
import CredentialDetailPage from "./pages/CredentialDetailPage";
import CredentialFormPage from "./pages/CredentialFormPage";
import CredentialListPage from "./pages/CredentialListPage";
import DashboardPage from "./pages/DashboardPage";
import SettingsPage from "./pages/SettingsPage";
import SubjectDetailPage from "./pages/SubjectDetailPage";
import SubjectListPage from "./pages/SubjectListPage";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <SubjectListPage /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/subjects/:id", element: <SubjectDetailPage /> },
      { path: "/credentials", element: <CredentialListPage /> },
      { path: "/credentials/new", element: <CredentialFormPage /> },
      { path: "/credentials/:id", element: <CredentialDetailPage /> },
    ],
  },
]);