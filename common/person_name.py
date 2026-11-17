"""
Ghép họ tên hiển thị theo thứ tự tiếng Việt "Họ đệm Tên" từ hai cột lastname / firstname của Moodle.

Dữ liệu thật của trường không thống nhất: đa số tài khoản nhập lastname = họ đệm, firstname = tên
("Nguyễn Văn" + "An"), nhưng một số tài khoản (chủ yếu giảng viên) nhập ngược ("Lan" + "Phạm Thị").
full_name() nhận ra trường hợp nhập ngược bằng danh sách họ phổ biến và tự đảo lại; trường hợp không chắc
thì giữ nguyên thứ tự gốc.

Tên cần sửa tay (thêm dấu, sửa chính tả) đặt trong tệp CSV ngoài kho mã – mặc định var/name_overrides.csv,
đổi bằng biến LMS_NAME_OVERRIDES – gồm các cột user_id, ho_dem, ten. Tệp chứa tên người thật nên không đưa
vào git.
"""
from __future__ import annotations

import csv
import logging
import os
import unicodedata
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OVERRIDES = ROOT / "var" / "name_overrides.csv"

# Họ phổ biến của người Việt. Chữ có dấu so khớp đúng dấu ("Trân" không phải "Trần"); chữ gõ không dấu
# so khớp bỏ dấu ("Tran" khớp "Trần").
_SURNAMES = """
Nguyễn Trần Lê Phạm Hoàng Huỳnh Phan Vũ Võ Đặng Bùi Đỗ Hồ Ngô Dương Lý Đoàn Tạ Trương Đinh Lâm Mai Cao Hà Lương
Thái Tô Trịnh Đào Châu Kiều Hứa Lục Mạc Nông Quách Tăng Thân Từ Vương Lưu Kim La Tôn Chu Diệp Giang Hầu Khổng Lại
Phùng Triệu Ông Âu Bạch Bế Doãn Khúc Lò Mã Nghiêm Ninh Quan Sầm Tiêu Thạch Lữ Trình Khương Hàn Tống
""".split()
# Họ hay trùng với tên gọi: đứng một mình trong ô lastname thì vẫn có thể là tên ("Mai" + "Đỗ Văn")
_GIVEN_TOO = """Lương Quan Thái Lâm Mai Hà Châu Giang Kim Ninh Diệp Tú Từ Khương""".split()


def _plain(word: str) -> str:
    text = unicodedata.normalize("NFD", word.replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()


def _key(word: str) -> str:
    return unicodedata.normalize("NFC", word).lower()


_ACCENTED = frozenset(_key(s) for s in _SURNAMES)
_PLAIN = frozenset(_plain(s) for s in _SURNAMES)
_WEAK = frozenset(_key(s) for s in _GIVEN_TOO) | frozenset(_plain(s) for s in _GIVEN_TOO)


def _surname(word: str) -> bool:
    return _key(word) in _ACCENTED if _plain(word) != _key(word) else _plain(word) in _PLAIN


def is_swapped(lastname: str, firstname: str) -> bool:
    """
    True khi tài khoản nhập ngược (ô lastname chứa tên, ô firstname chứa họ đệm). Chỉ kết luận khi chắc:
    - firstname có từ hai chữ và kết thúc bằng "Thị" (chữ đệm, không bao giờ là tên): "Lan" + "Phạm Thị";
    - lastname chỉ một chữ, firstname từ hai chữ bắt đầu bằng họ (ngược quy ước của tệp xuất, nơi lastname là
      họ đệm nhiều chữ), và chữ ở lastname không phải họ hoặc là họ hay dùng làm tên: "Minh" + "Lê Hoàng",
      "Mai" + "Đỗ Văn". "Lê" + "Thiên Ân" và "Trần" + "Nguyễn Văn A" giữ nguyên.
    Các trường hợp khác (kể cả tên người dân tộc thiểu số có thứ tự riêng) giữ nguyên; sửa tay bằng tệp tên.
    """
    last, first = (lastname or "").split(), (firstname or "").split()
    if not last or not first:
        return False
    if len(first) >= 2 and _plain(first[-1]) == "thi" and _plain(last[-1]) != "thi":
        return True
    return (len(last) == 1 and len(first) >= 2 and _surname(first[0])
            and (not _surname(last[0]) or _key(last[0]) in _WEAK or _plain(last[0]) in _WEAK))


@lru_cache(maxsize=4)
def _overrides(path: str) -> dict[int, str]:
    p = Path(path)
    if not p.is_file():
        return {}
    result: dict[int, str] = {}
    with p.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                user_id = int(row["user_id"])
            except (KeyError, TypeError, ValueError):
                continue
            name = " ".join(f"{row.get('ho_dem') or ''} {row.get('ten') or ''}".split())
            if name:
                result[user_id] = name
    log.info("Đã đọc %d tên sửa tay từ %s", len(result), p)
    return result


def overrides_path() -> str:
    return os.getenv("LMS_NAME_OVERRIDES") or str(DEFAULT_OVERRIDES)


def full_name(lastname: str | None, firstname: str | None, user_id: int | None = None) -> str:
    """Họ tên hiển thị "Họ đệm Tên": ưu tiên tên sửa tay, sau đó tự đảo khi phát hiện nhập ngược."""
    if user_id is not None:
        fixed = _overrides(overrides_path()).get(int(user_id))
        if fixed:
            return fixed
    last, first = (lastname or "").strip(), (firstname or "").strip()
    if is_swapped(last, first):
        last, first = first, last
    return " ".join(f"{last} {first}".split())
