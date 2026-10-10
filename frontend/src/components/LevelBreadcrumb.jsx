/**
 * Góp ý 3 – Thanh cấp xem: Toàn trường › Khoa › Môn học › Sinh viên. Cấp hiện tại tô đậm; nhấn cấp trên để quay lại.
 * Học kỳ đang chọn đi theo URL (?ay=…&sem=…).
 */
import { Link } from "react-router-dom";

export default function LevelBreadcrumb({ level, faculty, course, search = "" }) {
  const steps = [
    { key: "school", label: "Toàn trường", to: `/admin${search}` },
    { key: "faculty", label: faculty?.name ?? "Khoa", to: faculty ? `/admin/faculties/${faculty.id}${search}` : null },
    { key: "course", label: course?.name ?? "Môn học", to: course ? `/admin/courses/${course.id}${search}` : null },
    { key: "student", label: "Sinh viên", to: null },
  ];
  const current = steps.findIndex((s) => s.key === level);
  return (
    <nav className="level-crumb" aria-label="Cấp xem">
      {steps.map((s, i) => (
        <span key={s.key} className="level-step">
          {i > 0 && <span className="sep" aria-hidden>›</span>}
          {i < current && s.to ? <Link to={s.to}>{s.label}</Link>
            : <span className={i === current ? "on" : "off"} aria-current={i === current ? "page" : undefined}>{s.label}</span>}
        </span>
      ))}
    </nav>
  );
}
