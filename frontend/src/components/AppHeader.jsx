import { Button, Dropdown, Tooltip } from "antd";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useEtlStatus, useFilters } from "../api/hooks.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { fmtDateTime } from "../utils/format.js";
import MetricInfo from "./MetricInfo.jsx";

const ROLE_LABEL = { ADMIN: "Quản trị viên", TEACHER: "Giảng viên" };
const JOB_LABEL = {
  traffic: "Lưu lượng (5 phút)", course_progress: "Tiến độ môn (mỗi giờ)", student_risk: "Cảnh báo (2 giờ)",
  nightly: "Chốt số liệu đêm", maintenance: "Bảo trì tuần", backfill: "Nạp lịch sử",
  auto_prompt: "Nhắc tự động", message_dispatch: "Gửi tin",
};

function DataFreshness() {
  const { data: filters } = useFilters();
  const { data: jobs } = useEtlStatus();
  const latest = (jobs ?? []).map((j) => j.last_success_at).filter(Boolean).sort().at(-1);
  const detail = (
    <div style={{ fontSize: 12 }}>
      <div>Thời điểm tham chiếu dữ liệu: <b>{fmtDateTime(filters?.as_of)}</b></div>
      <div>ETL cập nhật gần nhất: <b>{latest ? fmtDateTime(latest) : "–"}</b></div>
      {(jobs ?? []).map((j) => (
        <div key={j.job_name}>{JOB_LABEL[j.job_name] ?? j.job_name}: {j.last_success_at ? fmtDateTime(j.last_success_at) : "chưa chạy"}</div>
      ))}
    </div>
  );
  return (
    <Tooltip title={detail} placement="bottomRight">
      <span className="updated" style={{ cursor: "help" }}>
        Dữ liệu: {fmtDateTime(filters?.as_of)}
      </span>
    </Tooltip>
  );
}

/** Mục menu có nhánh con (vd "Hệ thống"): mở danh sách liên kết, sáng lên khi đang ở một trang con. */
function NavGroup({ label, children }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const active = children.some((c) => pathname.startsWith(c.to));
  return (
    <Dropdown trigger={["click"]}
      menu={{ items: children.map((c) => ({ key: c.to, label: c.label })), selectedKeys: [pathname],
        onClick: ({ key }) => navigate(key) }}>
      <a href="#" role="button" className={active ? "active" : undefined} onClick={(e) => e.preventDefault()}>
        {label}
      </a>
    </Dropdown>
  );
}

export default function AppHeader({ links, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const base = user.role === "ADMIN" ? "/admin" : "/teacher";
  const menu = {
    items: [
      { key: "who", label: `${user.full_name ?? user.username} – ${ROLE_LABEL[user.role]}`, disabled: true },
      { type: "divider" },
      { key: "account", label: "Tài khoản & đổi mật khẩu" },
      { key: "help", label: "Hướng dẫn sử dụng" },
      { type: "divider" },
      { key: "logout", label: "Đăng xuất", danger: true },
    ],
    onClick: ({ key }) => {
      if (key === "logout") logout();
      else if (key === "account") navigate(`${base}/account`);
      else if (key === "help") navigate(`${base}/help`);
    },
  };
  return (
    <header className="app-header">
      <div className="app-logo"><span className="app-logo-mark" aria-hidden />LMS Analytics</div>
      {children}
      <nav className="app-nav" aria-label="Điều hướng chính">
        {links.map((link) => (link.children
          ? <NavGroup key={link.label} label={link.label}>{link.children}</NavGroup>
          : <NavLink key={link.to} to={link.to} end={link.end}
            className={({ isActive }) => (isActive || link.match?.some((m) => pathname.startsWith(m)) ? "active" : undefined)}>
            {link.label}</NavLink>))}
      </nav>
      <div className="app-header-meta">
        <DataFreshness />
        <span className="header-info"><MetricInfo metric={["enrolled", "active_rate", "risk_level", "traffic"]} label="Nguồn dữ liệu" /></span>
        <Dropdown menu={menu} trigger={["click"]}>
          <Button type="text" style={{ color: "#fff" }} aria-label="Tài khoản">{user.full_name ?? user.username}</Button>
        </Dropdown>
      </div>
    </header>
  );
}
