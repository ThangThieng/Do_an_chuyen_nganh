import { Select } from "antd";
import { useEffect, useState } from "react";
import { Outlet, useMatch, useNavigate } from "react-router-dom";
import { useTeacherCourses } from "../api/hooks.js";
import AppHeader from "../components/AppHeader.jsx";

/** SPEC 5.3 + v1.2: LOGO · Môn: [chọn môn] · Cảnh báo · Tiến độ lớp · Thiết lập cảnh báo · Can thiệp · Trợ giúp · tài khoản */
export default function TeacherLayout() {
  const match = useMatch("/teacher/courses/:courseId/:tab");
  const courseId = match?.params.courseId;
  const tab = match?.params.tab ?? "risk";
  const navigate = useNavigate();
  const { data, isLoading } = useTeacherCourses();
  // Ở trang không gắn môn (Trợ giúp, Tài khoản) vẫn giữ môn đang xem gần nhất để quay lại được
  const [lastCourse, setLastCourse] = useState();
  useEffect(() => {
    if (!courseId) return;
    setLastCourse(courseId);
    try { sessionStorage.setItem("lms.lastCourse", courseId); } catch { /* trình duyệt chặn lưu trữ: bỏ qua */ }
  }, [courseId]);
  const activeCourse = courseId ?? lastCourse ?? data?.items?.[0]?.course_id;

  const links = [
    ...(activeCourse
      ? [{ to: `/teacher/courses/${activeCourse}/risk`, label: "Cảnh báo" },
        { to: `/teacher/courses/${activeCourse}/progress`, label: "Tiến độ lớp" },
        { to: `/teacher/courses/${activeCourse}/rules`, label: "Thiết lập cảnh báo" },
        { to: `/teacher/courses/${activeCourse}/interventions`, label: "Can thiệp" }]
      : []),
    { to: "/teacher/help", label: "Trợ giúp" },
  ];

  return (
    <>
      <AppHeader links={links}>
        <Select
          aria-label="Chọn môn học"
          style={{ width: 320, maxWidth: "40vw" }}
          loading={isLoading}
          value={activeCourse ? Number(activeCourse) : undefined}
          placeholder="Chọn môn học"
          onChange={(id) => navigate(`/teacher/courses/${id}/${tab}`)}
          options={(data?.items ?? []).map((c) => ({
            value: c.course_id,
            label: `${c.shortname} – ${c.fullname}`,
          }))}
          showSearch
          optionFilterProp="label"
          popupMatchSelectWidth={false}
        />
      </AppHeader>
      <main className="page"><Outlet /></main>
    </>
  );
}
