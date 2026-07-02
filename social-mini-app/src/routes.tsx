import { Navigate, createBrowserRouter } from "react-router-dom";
import { useAuth } from "./auth/useAuth";
import { Layout } from "./navigation/Layout";
import CredentialDetailPage from "./pages/Credenticals/CredentialDetail";
import CredentialFormPage from "./pages/Credenticals/CredentialForm";
import CredentialListPage from "./pages/Credenticals";
import DashboardPage from "./pages/DashboardPage";
import SettingsPage from "./pages/SettingsPage";
import SubjectDetailPage from "./pages/Subjects/SubjectDetail";
import SubjectListPage from "./pages/Subjects";

function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <SubjectListPage /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/subjects/:id", element: <SubjectDetailPage /> },
      {
        path: "/credentials",
        element: <AdminGuard><CredentialListPage /></AdminGuard>,
      },
      {
        path: "/credentials/new",
        element: <AdminGuard><CredentialFormPage /></AdminGuard>,
      },
      {
        path: "/credentials/:id",
        element: <AdminGuard><CredentialDetailPage /></AdminGuard>,
      },
    ],
  },
]);