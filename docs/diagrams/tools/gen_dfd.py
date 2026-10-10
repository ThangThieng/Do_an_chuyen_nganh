"""
Sinh sơ đồ luồng dữ liệu (DFD) theo quy ước D1–D6 dưới dạng SVG, gom vào một file HTML để chụp thành PNG.

Bố cục chuẩn cho một yêu cầu:
            [Người dùng]
             D1 ↓   ↑ D6
[Thiết bị nhập] —D2→ (Xử lý) —D5→ [Thiết bị xuất]
             D3 ↑   ↓ D4
            ═ Bộ nhớ phụ ═

    python docs/diagrams/tools/gen_dfd.py   -> docs/diagrams/tools/dfd.html
"""
from __future__ import annotations

import html
from pathlib import Path

OUT = Path(__file__).with_name("dfd.html")
W, H = 760, 520
CX, CY, R = 380, 262, 78
FONT = "Arial, 'Segoe UI', sans-serif"

# (mã, người dùng, tên xử lý, thiết bị nhập hoặc None, thiết bị xuất hoặc None,
#  danh sách bộ nhớ phụ [(tên, có D3, có D4)])
DFDS = [
    ("dfd_dang_nhap", "Người dùng", "Đăng nhập", None, None, [("TÀI KHOẢN", True, True)]),
    ("dfd_doi_mat_khau", "Người dùng", "Đổi mật khẩu", None, None, [("TÀI KHOẢN", True, True)]),
    ("dfd_thong_ke_phan_cap", "Quản trị viên", "Thống kê phân cấp\nKhoa – Môn – SV", None, None,
     [("TIẾN ĐỘ MÔN THEO NGÀY", True, False), ("CẢNH BÁO SINH VIÊN", True, False)]),
    ("dfd_luu_luong", "Quản trị viên", "Theo dõi\nlưu lượng", None, None,
     [("LƯU LƯỢNG THEO GIỜ", True, False), ("MẪU NGƯỜI ONLINE", True, False)]),
    ("dfd_xuat_bao_cao", "Quản trị viên", "Xuất báo cáo", None, "Tệp Excel / PDF\n(máy in)",
     [("BẢNG FACT", True, False)]),
    ("dfd_danh_muc", "Quản trị viên", "Tra cứu\ndanh mục môn", None, None,
     [("TIẾN ĐỘ MÔN THEO NGÀY", True, False), ("TÀI KHOẢN", True, False)]),
    ("dfd_quan_ly_nguoi_dung", "Quản trị viên", "Quản lý\nngười dùng", None, None, [("TÀI KHOẢN", True, True)]),
    ("dfd_nhat_ky_etl", "Quản trị viên", "Xem\nnhật ký ETL", None, None, [("NHẬT KÝ ETL", True, False)]),
    ("dfd_sao_luu", "Quản trị viên", "Sao lưu\ndữ liệu", None, "Tệp sao lưu\n(.zip)",
     [("CSDL PHÂN TÍCH", True, False)]),
    ("dfd_phuc_hoi", "Quản trị viên", "Phục hồi\ndữ liệu", "Tệp sao lưu\n(.zip)", None,
     [("CSDL PHÂN TÍCH", True, True)]),
    ("dfd_canh_bao", "Giảng viên", "Xem cảnh báo\nsinh viên", None, None,
     [("CẢNH BÁO SINH VIÊN", True, False), ("TIẾN ĐỘ MÔN THEO NGÀY", True, False)]),
    ("dfd_chi_tiet_sv", "Giảng viên", "Xem chi tiết\nsinh viên", None, None,
     [("CẢNH BÁO SINH VIÊN", True, False), ("NHẬT KÝ CAN THIỆP", True, False)]),
    ("dfd_can_thiep", "Giảng viên", "Ghi nhận\ncan thiệp", None, None,
     [("CẢNH BÁO SINH VIÊN", True, False), ("NHẬT KÝ CAN THIỆP", False, True)]),
    ("dfd_xuat_canh_bao", "Giảng viên", "Xuất danh sách\ncảnh báo", None, "Tệp Excel / PDF\n(máy in)",
     [("CẢNH BÁO SINH VIÊN", True, False)]),
    ("dfd_tien_do_lop", "Giảng viên", "Xem\ntiến độ lớp", None, None,
     [("TIẾN ĐỘ MÔN THEO NGÀY", True, False), ("CẢNH BÁO SINH VIÊN", True, False)]),
    ("dfd_etl_rui_ro", "Bộ lập lịch ETL", "Chấm điểm\nrủi ro (ETL)", None, None,
     [("CSDL MOODLE", True, False), ("CẢNH BÁO SINH VIÊN\n+ NHẬT KÝ ETL", True, True)]),
]


def text(x: float, y: float, label: str, size: int = 15, weight: str = "normal", anchor: str = "middle") -> str:
    lines = label.split("\n")
    start = y - (len(lines) - 1) * size * 0.6
    spans = "".join(f'<tspan x="{x}" y="{start + i * size * 1.2:.1f}">{html.escape(line)}</tspan>'
                    for i, line in enumerate(lines))
    return (f'<text font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" fill="#111">{spans}</text>')


def arrow(x1, y1, x2, y2, label, lx, ly) -> str:
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#222" stroke-width="1.6" marker-end="url(#ah)"/>'
            + text(lx, ly, label, 14, "bold"))


def box(x, y, w, h, label) -> str:
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="#222" stroke-width="1.6"/>'
            + text(x + w / 2, y + h / 2, label, 15))


def store(x, y, w, label) -> str:
    h = 44
    return (f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="#222" stroke-width="1.6"/>'
            f'<line x1="{x}" y1="{y + h}" x2="{x + w}" y2="{y + h}" stroke="#222" stroke-width="1.6"/>'
            + text(x + w / 2, y + h / 2, label, 13))


def dfd(code, user, process, device_in, device_out, stores) -> str:
    parts = ['<defs><marker id="ah" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">'
             '<path d="M0,0 L10,4 L0,8 z" fill="#222"/></marker></defs>',
             f'<rect width="{W}" height="{H}" fill="#fff"/>']
    # Người dùng
    parts.append(box(CX - 95, 22, 190, 50, user))
    parts.append(arrow(CX - 30, 72, CX - 30, CY - R + 4, "D1", CX - 52, (72 + CY - R) / 2))
    parts.append(arrow(CX + 30, CY - R + 4, CX + 30, 72, "D6", CX + 52, (72 + CY - R) / 2))
    # Xử lý
    parts.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="#F4F7FB" stroke="#222" stroke-width="1.6"/>')
    parts.append(text(CX, CY, process, 15, "bold"))
    # Thiết bị nhập / xuất
    if device_in:
        parts.append(box(22, CY - 30, 170, 60, device_in))
        parts.append(arrow(192, CY, CX - R - 2, CY, "D2", (192 + CX - R) / 2, CY - 14))
    if device_out:
        parts.append(box(W - 192, CY - 30, 170, 60, device_out))
        parts.append(arrow(CX + R + 2, CY, W - 192, CY, "D5", (CX + R + W - 192) / 2, CY - 14))
    # Bộ nhớ phụ
    n = len(stores)
    width = 250 if n > 1 else 300
    gap = 40
    total = n * width + (n - 1) * gap
    top = CY + R + 80
    for i, (name, d3, d4) in enumerate(stores):
        x = CX - total / 2 + i * (width + gap)
        mid = x + width / 2
        parts.append(store(x, top, width, name))
        # điểm trên biên hình tròn hướng về kho
        dx, dy = mid - CX, top - CY
        dist = (dx * dx + dy * dy) ** 0.5
        ex, ey = CX + dx / dist * R, CY + dy / dist * R
        off = 18
        if d3 and d4:
            parts.append(arrow(mid - off, top, ex - off, ey + 2, "D3", (mid + ex) / 2 - off - 20, (top + ey) / 2))
            parts.append(arrow(ex + off, ey + 2, mid + off, top, "D4", (mid + ex) / 2 + off + 20, (top + ey) / 2))
        elif d3:
            parts.append(arrow(mid, top, ex, ey + 2, "D3", (mid + ex) / 2 - 20, (top + ey) / 2))
        elif d4:
            parts.append(arrow(ex, ey + 2, mid, top, "D4", (mid + ex) / 2 - 20, (top + ey) / 2))
    return (f'<svg id="{code}" xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">{"".join(parts)}</svg>')


def context_diagram() -> str:
    """DFD mức ngữ cảnh: toàn hệ thống là một xử lý, 4 tác nhân ngoài."""
    w, h = 1120, 520
    cx, cy, r = 560, 190, 105
    p = ['<defs><marker id="ah" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">'
         '<path d="M0,0 L10,4 L0,8 z" fill="#222"/></marker></defs>', f'<rect width="{w}" height="{h}" fill="#fff"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#F4F7FB" stroke="#222" stroke-width="1.6"/>',
         text(cx, cy, "0\nHệ thống\nLMS Analytics", 17, "bold")]

    def line(x1, y1, x2, y2):
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#222" stroke-width="1.5" '
                'marker-end="url(#ah)"/>')

    def label(x, y, value):
        return text(x, y, value, 13).replace('<text ', '<text stroke="#fff" stroke-width="5" paint-order="stroke" ', 1)

    edge = lambda dy: round((r * r - dy * dy) ** 0.5, 1)
    # Quản trị viên (trái) và Giảng viên (phải): một đường vào, một đường ra
    p.append(box(20, cy - 40, 200, 80, "Quản trị viên"))
    p.append(line(220, cy - 22, cx - edge(22), cy - 22))
    p.append(label((220 + cx - r) / 2, cy - 60, "bộ lọc, thao tác quản trị,\ntệp sao lưu cần phục hồi"))
    p.append(line(cx - edge(22), cy + 22, 222, cy + 22))
    p.append(label((220 + cx - r) / 2, cy + 62, "biểu đồ, báo cáo Excel/PDF,\ntài khoản, tệp sao lưu"))
    p.append(box(w - 220, cy - 40, 200, 80, "Giảng viên"))
    p.append(line(w - 220, cy - 22, cx + edge(22), cy - 22))
    p.append(label((w - 220 + cx + r) / 2, cy - 60, "chọn môn, bộ lọc,\nghi nhận can thiệp"))
    p.append(line(cx + edge(22), cy + 22, w - 222, cy + 22))
    p.append(label((w - 220 + cx + r) / 2, cy + 62, "danh sách cảnh báo, chi tiết SV,\ntiến độ lớp, tệp Excel/PDF"))
    # Bộ lập lịch (dưới trái) và Moodle (dưới phải): chỉ luồng vào
    p.append(box(170, h - 100, 200, 70, "Bộ lập lịch ETL"))
    p.append(line(370, h - 70, cx - 70, cy + 78))
    p.append(label(330, h - 160, "kích hoạt job theo lịch"))
    p.append(box(w - 370, h - 100, 200, 70, "Moodle LMS\n(CSDL moodle_src)"))
    p.append(line(w - 370, h - 70, cx + 70, cy + 78))
    p.append(label(w - 250, h - 165, "khóa học, ghi danh, nhật ký,\nđiểm danh, bài nộp (chỉ đọc)"))
    return f'<svg id="dfd_ngu_canh" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(p)}</svg>'


def main() -> None:
    body = context_diagram() + "".join(dfd(*spec) for spec in DFDS)
    OUT.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;background:#fff}}'
                   f'svg{{display:block;margin:0 0 20px}}</style></head><body>{body}</body></html>', encoding="utf-8")
    print(f"Đã ghi {OUT} ({len(DFDS) + 1} sơ đồ)")


if __name__ == "__main__":
    main()
