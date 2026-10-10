/** React Query hook cho từng endpoint (SPEC 5.1). */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { del, get, post, put } from "./client.js";

const termParams = (term) => (term?.academic_year && term?.semester
  ? { academic_year: term.academic_year, semester: term.semester }
  : {});

// ----------------------------------------------------------------------------- dùng chung
export const useFilters = () => useQuery({
  queryKey: ["filters"], queryFn: () => get("/filters"), staleTime: 5 * 60_000,
});

export const useEtlStatus = () => useQuery({
  queryKey: ["etl-status"], queryFn: () => get("/etl/status"), refetchInterval: 5 * 60_000,
});

// ----------------------------------------------------------------------------- Admin 1.1
export const useKpis = (term, facultyId) => useQuery({
  queryKey: ["kpis", term, facultyId],
  queryFn: () => get("/admin/overview/kpis", { ...termParams(term), faculty_id: facultyId }),
  enabled: !!term, placeholderData: keepPreviousData, refetchInterval: 60_000,
});

export const useEnrollmentByFaculty = (term) => useQuery({
  queryKey: ["by-faculty", term],
  queryFn: () => get("/admin/enrollment/by-faculty", termParams(term)),
  enabled: !!term, placeholderData: keepPreviousData,
});

export const useFacultyCourses = (facultyId, term, sort = "active_rate", order = "desc") => useQuery({
  queryKey: ["faculty-courses", facultyId, term, sort, order],
  queryFn: () => get(`/admin/enrollment/faculties/${facultyId}/courses`, { ...termParams(term), sort, order }),
  enabled: !!facultyId && !!term, placeholderData: keepPreviousData,
});

export const useCourseStudents = (courseId, params) => useQuery({
  queryKey: ["course-students", courseId, params],
  queryFn: () => get(`/admin/enrollment/courses/${courseId}/students`, params),
  enabled: !!courseId, placeholderData: keepPreviousData,
});

// ----------------------------------------------------------------------------- Admin 1.2
export const useTrafficHourly = (from, to) => useQuery({
  queryKey: ["traffic-hourly", from, to],
  queryFn: () => get("/admin/traffic/hourly", { from, to }),
  placeholderData: keepPreviousData,
});

export const useTrafficRealtime = () => useQuery({
  queryKey: ["traffic-realtime"], queryFn: () => get("/admin/traffic/realtime"),
  refetchInterval: 60_000,           // SPEC 5.1: frontend gọi lại mỗi 60 giây
});

export const useTrafficHeatmap = (weeks) => useQuery({
  queryKey: ["traffic-heatmap", weeks], queryFn: () => get("/admin/traffic/heatmap", { weeks }),
  placeholderData: keepPreviousData,
});

// ----------------------------------------------------------------------------- Admin 1.3
export const useReportPreview = (params, enabled) => useQuery({
  queryKey: ["report-preview", params],
  queryFn: () => get("/admin/reports/preview", params),
  enabled, placeholderData: keepPreviousData,
});

// ----------------------------------------------------------------------------- Giảng viên
export const useTeacherCourses = () => useQuery({
  queryKey: ["teacher-courses"], queryFn: () => get("/teacher/courses"),
});

export const useRiskSummary = (courseId) => useQuery({
  queryKey: ["risk-summary", courseId], queryFn: () => get(`/teacher/courses/${courseId}/risk-summary`),
  enabled: !!courseId,
});

export const useRiskStudents = (courseId, params) => useQuery({
  queryKey: ["risk-students", courseId, params],
  queryFn: () => get(`/teacher/courses/${courseId}/students`, params),
  enabled: !!courseId, placeholderData: keepPreviousData,
});

export const useAdminStudentCompare = (courseId, userId) => useQuery({
  queryKey: ["admin-student-compare", courseId, userId],
  queryFn: () => get(`/admin/courses/${courseId}/students/${userId}/compare`),
  enabled: !!courseId && !!userId,
});

export const useStudentDetail = (courseId, userId) => useQuery({
  queryKey: ["student-detail", courseId, userId],
  queryFn: () => get(`/teacher/courses/${courseId}/students/${userId}`),
  enabled: !!courseId && !!userId,
});

export const useStudentCompare = (courseId, userId) => useQuery({
  queryKey: ["student-compare", courseId, userId],
  queryFn: () => get(`/teacher/courses/${courseId}/students/${userId}/compare`),
  enabled: !!courseId && !!userId,
});

export const useCourseProgress = (courseId, granularity) => useQuery({
  queryKey: ["course-progress", courseId, granularity],
  queryFn: () => get(`/teacher/courses/${courseId}/progress`, { granularity }),
  enabled: !!courseId, placeholderData: keepPreviousData,
});

export function useCreateIntervention(courseId, userId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => post(`/teacher/courses/${courseId}/students/${userId}/interventions`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["student-detail", courseId, userId] }),
  });
}

// ----------------------------------------------------------------------------- Tài khoản
export const useChangePassword = () => useMutation({
  mutationFn: (body) => post("/auth/change-password", body),
});

// ----------------------------------------------------------------------------- Hệ thống (Admin)
export const useUsers = () => useQuery({ queryKey: ["users"], queryFn: () => get("/admin/users") });

export function useSetUserActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, isActive }) => post(`/admin/users/${userId}/active`, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useResetPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId) => post(`/admin/users/${userId}/reset-password`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}

export const useEtlRuns = (params) => useQuery({
  queryKey: ["etl-runs", params], queryFn: () => get("/admin/etl/runs", params),
  placeholderData: keepPreviousData, refetchInterval: 60_000,
});

export const useCatalog = (term, facultyId) => useQuery({
  queryKey: ["catalog", term, facultyId],
  queryFn: () => get("/admin/catalog/courses", { ...termParams(term), faculty_id: facultyId }),
  enabled: !!term, placeholderData: keepPreviousData,
});

export const useBackups = () => useQuery({ queryKey: ["backups"], queryFn: () => get("/admin/backups") });

function useBackupMutation(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["backups"] }) });
}

export const useCreateBackup = () => useBackupMutation(() => post("/admin/backups", null, { timeout: 300_000 }));
export const useDeleteBackup = () => useBackupMutation((name) => del(`/admin/backups/${encodeURIComponent(name)}`));

export function useRestoreBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    // Phục hồi nạp lại toàn bộ bảng fact: đo được ~40 giây trên bộ dữ liệu demo
    mutationFn: (name) => post(`/admin/backups/${encodeURIComponent(name)}/restore`, { confirm_name: name },
      { timeout: 600_000 }),
    // Mọi số liệu trên các màn hình khác đã đổi -> xóa toàn bộ cache truy vấn
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

// ----------------------------------------------------------------------------- v1.2 – minh bạch (góp ý 4)
export const useMetaMetrics = () => useQuery({
  queryKey: ["meta-metrics"], queryFn: () => get("/meta/metrics"), staleTime: 30 * 60_000,
});

export const useRiskRule = (courseId, enabled = true) => useQuery({
  queryKey: ["meta-risk-rule", courseId ?? "school"],
  queryFn: () => get("/meta/risk-rule", { course_id: courseId }), enabled, staleTime: 60_000,
});

export const useFreshness = (enabled = true) => useQuery({
  queryKey: ["meta-freshness"], queryFn: () => get("/meta/freshness"), enabled, staleTime: 60_000,
});

export const useChannelModes = () => useQuery({
  queryKey: ["meta-channels"], queryFn: () => get("/meta/channels"), staleTime: 60_000,
});

// ----------------------------------------------------------------------------- v1.2 – so sánh & xu hướng (góp ý 1, 2)
export const useFacultyCompare = (term) => useQuery({
  queryKey: ["compare-faculties", term],
  queryFn: () => get("/admin/compare/faculties", termParams(term)),
  enabled: !!term, placeholderData: keepPreviousData,
});

/** scope: {facultyId?, courseId?} cho Admin; teacherCourseId cho giảng viên. */
export const useRiskTrend = ({ term, facultyId, courseId, teacherCourseId, granularity = "week" }) => useQuery({
  queryKey: ["risk-trend", term, facultyId, courseId, teacherCourseId, granularity],
  queryFn: () => (teacherCourseId
    ? get(`/teacher/courses/${teacherCourseId}/risk-trend`, { granularity })
    : get("/admin/risk-trend", { ...termParams(term), faculty_id: facultyId, course_id: courseId, granularity })),
  enabled: !!teacherCourseId || !!term, placeholderData: keepPreviousData,
});

// Trang Môn học của quản trị viên (chỉ đọc)
export const useAdminRiskSummary = (courseId) => useQuery({
  queryKey: ["admin-risk-summary", courseId], queryFn: () => get(`/admin/courses/${courseId}/risk-summary`),
  enabled: !!courseId,
});

export const useAdminRiskStudents = (courseId, params) => useQuery({
  queryKey: ["admin-risk-students", courseId, params],
  queryFn: () => get(`/admin/courses/${courseId}/risk-students`, params),
  enabled: !!courseId, placeholderData: keepPreviousData,
});

export const useAdminStudentDetail = (courseId, userId) => useQuery({
  queryKey: ["admin-student-detail", courseId, userId],
  queryFn: () => get(`/admin/courses/${courseId}/students/${userId}`),
  enabled: !!courseId && !!userId,
});

// ----------------------------------------------------------------------------- v1.2 – chức năng 1: luật theo môn
export const useCourseRules = (courseId) => useQuery({
  queryKey: ["course-rules", courseId], queryFn: () => get(`/teacher/courses/${courseId}/risk-rules`),
  enabled: !!courseId,
});

export const usePreviewRules = (courseId) => useMutation({
  mutationFn: (body) => post(`/teacher/courses/${courseId}/risk-rules/preview`, body),
});

function useRulesMutation(courseId, fn) {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => queryClient.invalidateQueries() });
}

export const useSaveRules = (courseId) => useRulesMutation(courseId, (body) => put(`/teacher/courses/${courseId}/risk-rules`, body));
export const useResetRules = (courseId) => useRulesMutation(courseId, () => del(`/teacher/courses/${courseId}/risk-rules`));

// ----------------------------------------------------------------------------- v1.2 – chức năng 2: trung tâm can thiệp
export const useContactList = (courseId, params) => useQuery({
  queryKey: ["contact-list", courseId, params],
  queryFn: () => get(`/teacher/courses/${courseId}/contact-list`, params),
  enabled: !!courseId, placeholderData: keepPreviousData,
});

export const useMessageTemplates = () => useQuery({
  queryKey: ["message-templates"], queryFn: () => get("/teacher/message-templates"),
});

export function useTemplateMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, body, remove }) => (remove ? del(`/teacher/message-templates/${templateId}`)
      : templateId ? put(`/teacher/message-templates/${templateId}`, body) : post("/teacher/message-templates", body)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["message-templates"] }),
  });
}

export const usePreviewMessages = (courseId) => useMutation({
  mutationFn: (body) => post(`/teacher/courses/${courseId}/messages/preview`, body),
});

function invalidateMessaging(queryClient, courseId) {
  queryClient.invalidateQueries({ queryKey: ["messages", courseId] });
  queryClient.invalidateQueries({ queryKey: ["contact-list", courseId] });
  queryClient.invalidateQueries({ queryKey: ["student-detail", courseId] });
  queryClient.invalidateQueries({ queryKey: ["auto-prompts", courseId] });
}

export function useSendMessages(courseId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => post(`/teacher/courses/${courseId}/messages`, body, { timeout: 180_000 }),
    onSuccess: () => invalidateMessaging(queryClient, courseId),
  });
}

export const useMessages = (courseId, params) => useQuery({
  queryKey: ["messages", courseId, params],
  queryFn: () => get(`/teacher/courses/${courseId}/messages`, params),
  enabled: !!courseId, placeholderData: keepPreviousData, refetchInterval: 30_000,
});

export function useMessageAction(courseId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ messageId, action }) => post(`/teacher/courses/${courseId}/messages/${messageId}/${action}`),
    onSuccess: () => invalidateMessaging(queryClient, courseId),
  });
}

export const useAutoPrompts = (courseId) => useQuery({
  queryKey: ["auto-prompts", courseId], queryFn: () => get(`/teacher/courses/${courseId}/auto-prompts`),
  enabled: !!courseId,
});

export function useAutoPromptMutation(courseId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, body, remove, action }) => {
      if (action) return post(`/teacher/courses/${courseId}/auto-prompts/${ruleId}/${action}`);
      if (remove) return del(`/teacher/courses/${courseId}/auto-prompts/${ruleId}`);
      return ruleId ? put(`/teacher/courses/${courseId}/auto-prompts/${ruleId}`, body)
        : post(`/teacher/courses/${courseId}/auto-prompts`, body);
    },
    onSuccess: (_, vars) => { if (vars.action !== "dry-run") invalidateMessaging(queryClient, courseId); },
  });
}

// ----------------------------------------------------------------------------- v1.2 – kênh gửi tin (Admin)
export const useChannelStatus = () => useQuery({ queryKey: ["admin-channels"], queryFn: () => get("/admin/channels") });

export function useChannelTest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, to }) => post(`/admin/channels/test-${kind}`, kind === "email" ? { to } : undefined,
      { timeout: 90_000 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-channels"] });
      queryClient.invalidateQueries({ queryKey: ["meta-channels"] });
    },
  });
}
