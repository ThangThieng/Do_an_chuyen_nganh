import { Outlet } from "react-router-dom";
import AppHeader from "../components/AppHeader.jsx";

/**
 * Menu chính theo 5 nhánh: Nghiệp vụ/Báo cáo thống kê (Tổng quan, Lưu lượng, Báo cáo) · Danh mục ·
 * Hệ thống (Người dùng, Nhật ký ETL, Sao lưu & phục hồi) · Trợ giúp. Đổi mật khẩu/Đăng xuất nằm ở menu tài khoản.
 */
const LINKS = [
  { to: "/admin", label: "Tổng quan", end: true, match: ["/admin/faculties", "/admin/courses"] },
  { to: "/admin/traffic", label: "Lưu lượng" },
  { to: "/admin/reports", label: "Báo cáo" },
  { to: "/admin/catalog", label: "Danh mục" },
  {
    label: "Hệ thống",
    children: [
      { to: "/admin/users", label: "Quản lý người dùng" },
      { to: "/admin/etl", label: "Nhật ký ETL" },
      { to: "/admin/backups", label: "Sao lưu & phục hồi" },
      { to: "/admin/channels", label: "Kênh gửi tin" },
    ],
  },
  { to: "/admin/help", label: "Trợ giúp" },
];

export default function AdminLayout() {
  return (
    <>
      <AppHeader links={LINKS} />
      <main className="page"><Outlet /></main>
    </>
  );
}
