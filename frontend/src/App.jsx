import { Spin } from "antd";
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { homePath, useAuth } from "./auth/AuthContext.jsx";
import AdminLayout from "./layouts/AdminLayout.jsx";
import TeacherLayout from "./layouts/TeacherLayout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";

const AdminOverview = lazy(() => import("./pages/admin/AdminOverview.jsx"));
const AdminTraffic = lazy(() => import("./pages/admin/AdminTraffic.jsx"));
const AdminReports = lazy(() => import("./pages/admin/AdminReports.jsx"));
const AdminCatalog = lazy(() => import("./pages/admin/AdminCatalog.jsx"));
const AdminUsers = lazy(() => import("./pages/admin/AdminUsers.jsx"));
const AdminEtlLog = lazy(() => import("./pages/admin/AdminEtlLog.jsx"));
const AdminBackups = lazy(() => import("./pages/admin/AdminBackups.jsx"));
const AdminFaculty = lazy(() => import("./pages/admin/AdminFaculty.jsx"));
const AdminCourse = lazy(() => import("./pages/admin/AdminCourse.jsx"));
const AdminChannels = lazy(() => import("./pages/admin/AdminChannels.jsx"));
const AccountPage = lazy(() => import("./pages/AccountPage.jsx"));
const HelpPage = lazy(() => import("./pages/HelpPage.jsx"));
const TeacherHome = lazy(() => import("./pages/teacher/TeacherHome.jsx"));
const TeacherRisk = lazy(() => import("./pages/teacher/TeacherRisk.jsx"));
const TeacherProgress = lazy(() => import("./pages/teacher/TeacherProgress.jsx"));
const TeacherRules = lazy(() => import("./pages/teacher/TeacherRules.jsx"));
const TeacherInterventions = lazy(() => import("./pages/teacher/TeacherInterventions.jsx"));

export function PageSpinner() {
  return <div style={{ display: "grid", placeItems: "center", minHeight: 320 }}><Spin size="large" /></div>;
}

function RootRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? homePath(user) : "/login"} replace />;
}

const lazyPage = (Page) => <Suspense fallback={<PageSpinner />}><Page /></Suspense>;

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/admin" element={<ProtectedRoute role="ADMIN"><AdminLayout /></ProtectedRoute>}>
        <Route index element={lazyPage(AdminOverview)} />
        <Route path="faculties/:facultyId" element={lazyPage(AdminFaculty)} />
        <Route path="courses/:courseId" element={lazyPage(AdminCourse)} />
        <Route path="traffic" element={lazyPage(AdminTraffic)} />
        <Route path="reports" element={lazyPage(AdminReports)} />
        <Route path="catalog" element={lazyPage(AdminCatalog)} />
        <Route path="users" element={lazyPage(AdminUsers)} />
        <Route path="etl" element={lazyPage(AdminEtlLog)} />
        <Route path="backups" element={lazyPage(AdminBackups)} />
        <Route path="channels" element={lazyPage(AdminChannels)} />
        <Route path="account" element={lazyPage(AccountPage)} />
        <Route path="help" element={lazyPage(HelpPage)} />
      </Route>
      <Route path="/teacher" element={<ProtectedRoute role="TEACHER"><TeacherLayout /></ProtectedRoute>}>
        <Route index element={lazyPage(TeacherHome)} />
        <Route path="courses/:courseId" element={<Navigate to="risk" replace />} />
        <Route path="courses/:courseId/risk" element={lazyPage(TeacherRisk)} />
        <Route path="courses/:courseId/progress" element={lazyPage(TeacherProgress)} />
        <Route path="courses/:courseId/rules" element={lazyPage(TeacherRules)} />
        <Route path="courses/:courseId/interventions" element={lazyPage(TeacherInterventions)} />
        <Route path="account" element={lazyPage(AccountPage)} />
        <Route path="help" element={lazyPage(HelpPage)} />
      </Route>
      <Route path="*" element={<RootRedirect />} />
    </Routes>
  );
}
