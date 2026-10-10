/**
 * Cửa sổ chi tiết sinh viên (SPEC 5.3, v1.2): lý do cảnh báo · PHÂN TÍCH ĐIỂM RỦI RO (góp ý 4) · so sánh với lớp ·
 * hoạt động theo tuần · bài tập · lịch sử cảnh báo · can thiệp. Nút "Gửi tin nhắn Moodle" / "Gửi email" mở trình soạn
 * tin và gửi THẬT (chức năng 2); "Ghi chú", "Hẹn gặp" vẫn chỉ ghi nhật ký. readOnly: quản trị viên xem, không thao tác.
 */
import { Alert, App, Button, Col, Divider, Empty, Form, Input, List, Modal, Row, Skeleton, Space, Tag, Tooltip } from "antd";
import { useState } from "react";
import { errorMessage, errorText } from "../api/client.js";
import { useAdminStudentCompare, useAdminStudentDetail, useCreateIntervention, useRiskRule, useStudentCompare,
  useStudentDetail } from "../api/hooks.js";
import { StudentCompareChart, WeeklyActivityChart } from "../charts/StudentCharts.jsx";
import { ACTIONS, RISK } from "../theme/tokens.js";
import { fmtDate, fmtDateTime, fmtDaysSince, fmtShortDate, riskTransitions } from "../utils/format.js";
import MessageComposer from "./MessageComposer.jsx";
import MetricInfo from "./MetricInfo.jsx";
import ScoreBreakdown from "./ScoreBreakdown.jsx";
import { Rate, RiskBadge } from "./common.jsx";

// Nền nhạt + chữ đậm cùng tông (tag màu preset của Ant Design không đạt tương phản WCAG AA)
const ASSIGNMENT_TAG = {
  on_time: { tone: RISK.GREEN, text: "đúng hạn" },
  late: { tone: RISK.YELLOW, text: "trễ hạn" },
  missing: { tone: RISK.RED, text: "thiếu" },
  not_due: { tone: null, text: "chưa tới hạn" },
};

function assignmentState(a) {
  if (a.status === "submitted") return a.late ? "late" : "on_time";
  return a.status === "missing" ? "missing" : "not_due";
}

function NoteDialog({ action, student, courseId, onClose }) {
  const { message } = App.useApp();
  const mutation = useCreateIntervention(courseId, student.user_id);
  const [form] = Form.useForm();
  const meta = ACTIONS[action];

  async function submit({ content }) {
    try {
      await mutation.mutateAsync({ action_type: action, content });
      message.success(`Đã ghi nhận: ${meta.label}`);
      onClose();
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  return (
    <Modal open title={`${meta.label} – ${student.student_name}`} onCancel={onClose} okText="Ghi nhận"
      cancelText="Hủy" onOk={() => form.submit()} confirmLoading={mutation.isPending} destroyOnHidden>
      <Form form={form} layout="vertical" onFinish={submit}>
        <Form.Item name="content" label="Nội dung" rules={[{ max: 2000, message: "Tối đa 2.000 ký tự" }]}>
          <Input.TextArea rows={4} placeholder="vd: Đã nhắc nhở trên lớp, hẹn gặp thứ 5" showCount maxLength={2000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export default function StudentDetailModal({ courseId, userId, onClose, readOnly = false }) {
  const teacherDetail = useStudentDetail(readOnly ? null : courseId, userId);
  const adminDetail = useAdminStudentDetail(readOnly ? courseId : null, userId);
  const detail = readOnly ? adminDetail : teacherDetail;
  const teacherCompare = useStudentCompare(readOnly ? null : courseId, userId);
  const adminCompare = useAdminStudentCompare(readOnly ? courseId : null, userId);
  const compare = readOnly ? adminCompare : teacherCompare;
  const rule = useRiskRule(courseId);
  const [note, setNote] = useState(null);
  const [compose, setCompose] = useState(null);
  const s = detail.data;

  const title = s ? (
    <Space wrap size={[8, 4]}>
      <RiskBadge level={s.risk_level} />
      <span>{s.student_name}</span>
      <span className="muted" style={{ fontWeight: 400 }}>{s.student_code} · {s.email ?? "không có email"}</span>
      <Tooltip title="Xem bảng phân tích điểm bên dưới"><Tag>Điểm rủi ro {s.risk_score}</Tag></Tooltip>
    </Space>
  ) : "Chi tiết sinh viên";

  return (
    <Modal open={!!userId} onCancel={onClose} title={title} width={1080} destroyOnHidden
      footer={(
        <Space wrap>
          {!readOnly && (
            <>
              <Button type="primary" ghost disabled={!s} onClick={() => setCompose(["MOODLE"])}>Gửi tin nhắn Moodle</Button>
              <Button type="primary" ghost disabled={!s} onClick={() => setCompose(["EMAIL"])}>Gửi email</Button>
              <Button disabled={!s} onClick={() => setNote("NOTE")}>Ghi chú</Button>
              <Button disabled={!s} onClick={() => setNote("MEETING")}>Hẹn gặp</Button>
            </>
          )}
          <Button type="primary" onClick={onClose}>Đóng</Button>
        </Space>
      )}>
      {detail.error && <Alert type="error" showIcon message={errorText(detail.error)} />}
      {detail.isLoading && <Skeleton active paragraph={{ rows: 10 }} />}
      {s && (
        <>
          <Alert
            type={s.risk_level === "GREEN" ? "success" : s.risk_level === "YELLOW" ? "warning" : "error"}
            message={s.risk_reasons.length ? <>Lý do: {s.risk_reasons.join("; ")}</> : "Không có dấu hiệu bất thường"}
            description={(
              <Space wrap size={[16, 4]} className="muted" style={{ fontSize: 12 }}>
                <span>Vắng: <Rate value={s.absence_rate} /> ({s.absent_sessions}/{s.total_sessions} buổi)</span>
                <span>Bài tập: đã nộp {s.submitted_assignments}/{s.total_assignments} (trễ {s.late_submissions})</span>
                <span>Truy cập cuối: {fmtDaysSince(s.days_since_last_access)}</span>
                <span>Hoàn thành hoạt động: <Rate value={s.completion_rate} /></span>
                <span>Snapshot {fmtDate(s.snapshot_date)}</span>
              </Space>
            )}
          />

          {/* Tiêu đề mục có liên kết: dùng h4 thay Divider (separator không được chứa phần tử tương tác – WCAG) */}
          <div className="modal-section">
            <h4>Phân tích điểm rủi ro</h4>
            <MetricInfo metric={{ keys: ["risk_score", "risk_level"], courseId }} compact />
          </div>
          {rule.data ? <ScoreBreakdown s={s} rule={rule.data} /> : <Skeleton active paragraph={{ rows: 3 }} />}
          {s.attendance_detail?.length > 1 && (
            <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
              Theo hoạt động điểm danh: {s.attendance_detail.map((a) => `${a.name} vắng ${a.absent}/${a.sessions}`).join(" · ")}
              {s.max_consecutive_missing > 0 && ` · bỏ nộp liên tiếp tối đa ${s.max_consecutive_missing} bài`}
            </div>
          )}

          <Row gutter={[24, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} md={11}>
              <b>So sánh với trung bình lớp</b>
              {compare.data ? <StudentCompareChart metrics={compare.data.metrics} /> : <Skeleton active />}
            </Col>
            <Col xs={24} md={13}>
              <b>Hoạt động {s.weekly_activity.length} tuần</b>
              <WeeklyActivityChart weeks={s.weekly_activity} />
            </Col>
          </Row>

          <Divider orientation="left" plain>Bài tập</Divider>
          {s.assignment_detail.length ? (
            <Space wrap size={[6, 6]}>
              {s.assignment_detail.map((a) => {
                const state = ASSIGNMENT_TAG[assignmentState(a)];
                return (
                  <Tooltip key={a.assign_id ?? a.name} title={`Hạn ${fmtDateTime(a.duedate)}${a.submitted_at ? ` · nộp ${fmtDateTime(a.submitted_at)}` : ""}`}>
                    <Tag style={state.tone ? { color: state.tone.ink, background: state.tone.tint, borderColor: state.tone.color } : undefined}>
                      {a.name} – {state.text}
                    </Tag>
                  </Tooltip>
                );
              })}
            </Space>
          ) : <span className="muted">Môn chưa có bài tập</span>}

          <Divider orientation="left" plain>Lịch sử cảnh báo</Divider>
          <Space wrap size={[4, 6]}>
            {riskTransitions(s.risk_history).map((p, i) => (
              <span key={p.date}>
                {i > 0 && <span className="muted"> – </span>}
                <span className="muted">{fmtShortDate(p.date)} </span><RiskBadge level={p.risk_level} compact />
              </span>
            ))}
          </Space>

          <Divider orientation="left" plain>Can thiệp trước đây</Divider>
          {s.interventions.length ? (
            <List size="small" dataSource={s.interventions} renderItem={(i) => (
              <List.Item>
                <Space wrap size={[8, 2]} align="start">
                  <span className="muted">{fmtDateTime(i.created_at)}</span>
                  <Tag>{ACTIONS[i.action_type]?.label ?? i.action_type}</Tag>
                  {i.origin === "AUTO" && <Tag color="blue">Tự động</Tag>}
                  <span style={{ whiteSpace: "pre-line" }}>{i.content ?? <span className="muted">(không có nội dung)</span>}</span>
                  <span className="muted">– {i.teacher_name ?? `GV #${i.teacher_id}`}</span>
                  {i.risk_level_at_time && <RiskBadge level={i.risk_level_at_time} compact />}
                </Space>
              </List.Item>
            )} />
          ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chưa có can thiệp nào" />}

          {note && <NoteDialog action={note} student={s} courseId={courseId} onClose={() => setNote(null)} />}
          {compose && (
            <MessageComposer courseId={courseId} students={[s]} defaultChannels={compose}
              defaultPurpose={s.risk_level === "RED" ? "RISK_HIGH" : "CHECK_IN"} onClose={() => setCompose(null)} />
          )}
        </>
      )}
    </Modal>
  );
}
