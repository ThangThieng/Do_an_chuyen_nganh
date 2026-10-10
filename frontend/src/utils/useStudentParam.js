/**
 * Cấp Sinh viên (góp ý 3, kế hoạch Mục 3.1): cửa sổ chi tiết sinh viên gắn với tham số ?student=:userId trên URL.
 * - Mở cửa sổ = thêm một bước lịch sử: nút Back của trình duyệt đóng cửa sổ, quay về cấp Môn học.
 * - F5 hoặc đường dẫn chia sẻ mở lại đúng sinh viên.
 * - Đóng bằng nút: nếu bước lịch sử do chính trang này thêm thì lùi một bước (lịch sử không dư bước),
 *   còn nếu trang được mở thẳng với ?student= thì chỉ xóa tham số.
 * Các tham số khác (học kỳ ?ay=&sem=) giữ nguyên.
 */
import { useCallback } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

const OPENED_HERE = "studentOpenedHere";

export default function useStudentParam() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const raw = Number(params.get("student"));
  const userId = Number.isInteger(raw) && raw > 0 ? raw : null;

  const open = useCallback((id) => {
    setParams((prev) => {
      const p = new URLSearchParams(prev);
      p.set("student", String(id));
      return p;
    }, { replace: userId != null, state: { [OPENED_HERE]: true } });
  }, [setParams, userId]);

  const close = useCallback(() => {
    if (location.state?.[OPENED_HERE]) {
      navigate(-1);
      return;
    }
    setParams((prev) => {
      const p = new URLSearchParams(prev);
      p.delete("student");
      return p;
    }, { replace: true });
  }, [location.state, navigate, setParams]);

  return [userId, open, close];
}
