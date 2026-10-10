/** Tài khoản: thông tin người đăng nhập + đổi mật khẩu (kiểm tra ngay ở từng ô, kiểm tra quan hệ giữa các ô khi Lưu). */
import { Alert, App, Button, Card, Col, Descriptions, Form, Input, Row } from "antd";
import { errorMessage } from "../api/client.js";
import { useChangePassword } from "../api/hooks.js";
import { useAuth } from "../auth/AuthContext.jsx";

const ROLE_LABEL = { ADMIN: "Quản trị viên", TEACHER: "Giảng viên" };
const MIN_LENGTH = 8;

export default function AccountPage() {
  const { message } = App.useApp();
  const { user, applyToken } = useAuth();
  const [form] = Form.useForm();
  const change = useChangePassword();

  async function onFinish(values) {
    try {
      const data = await change.mutateAsync({ current_password: values.current, new_password: values.next });
      applyToken(data);
      form.resetFields();
      message.success("Đã đổi mật khẩu. Các phiên đăng nhập khác của tài khoản này đã bị đăng xuất.");
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={10}>
        <Card title="Thông tin tài khoản">
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Tên đăng nhập">{user.username}</Descriptions.Item>
            <Descriptions.Item label="Họ tên">{user.full_name ?? "–"}</Descriptions.Item>
            <Descriptions.Item label="Email">{user.email ?? "–"}</Descriptions.Item>
            <Descriptions.Item label="Vai trò">{ROLE_LABEL[user.role]}</Descriptions.Item>
          </Descriptions>
          <div className="muted" style={{ marginTop: 12, fontSize: 12 }}>
            Họ tên, email và vai trò được đồng bộ từ Moodle; muốn thay đổi, liên hệ quản trị viên.
          </div>
        </Card>
      </Col>
      <Col xs={24} lg={14}>
        <Card title="Đổi mật khẩu">
          <Alert type="info" showIcon style={{ marginBottom: 16 }}
            message={`Mật khẩu mới cần ít nhất ${MIN_LENGTH} ký tự, có cả chữ và số. Sau khi đổi, các phiên đăng nhập khác của tài khoản sẽ bị đăng xuất.`} />
          <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false} disabled={change.isPending}
            style={{ maxWidth: 420 }}>
            <Form.Item label="Mật khẩu hiện tại" name="current" rules={[{ required: true, message: "Nhập mật khẩu hiện tại" }]}>
              <Input.Password autoComplete="current-password" />
            </Form.Item>
            <Form.Item label="Mật khẩu mới" name="next" validateTrigger="onBlur" hasFeedback
              rules={[
                { required: true, message: "Nhập mật khẩu mới" },
                { min: MIN_LENGTH, message: `Ít nhất ${MIN_LENGTH} ký tự` },
                { pattern: /(?=.*\p{L})(?=.*\d)/u, message: "Cần có cả chữ và số" },
              ]}>
              <Input.Password autoComplete="new-password" />
            </Form.Item>
            <Form.Item label="Nhập lại mật khẩu mới" name="confirm" dependencies={["next"]} hasFeedback
              rules={[
                { required: true, message: "Nhập lại mật khẩu mới" },
                ({ getFieldValue }) => ({
                  validator: (_, value) => (!value || getFieldValue("next") === value
                    ? Promise.resolve() : Promise.reject(new Error("Hai lần nhập không khớp"))),
                }),
              ]}>
              <Input.Password autoComplete="new-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={change.isPending}>Lưu mật khẩu mới</Button>
          </Form>
        </Card>
      </Col>
    </Row>
  );
}
