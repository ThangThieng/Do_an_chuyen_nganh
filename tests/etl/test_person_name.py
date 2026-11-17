"""Ghép họ tên "Họ đệm Tên" từ lastname / firstname khi một số tài khoản nhập ngược hai ô."""
from __future__ import annotations

import pytest

from common import person_name
from common.person_name import full_name, is_swapped


@pytest.fixture(autouse=True)
def _no_override_file(monkeypatch, tmp_path):
    monkeypatch.setenv("LMS_NAME_OVERRIDES", str(tmp_path / "khong_co.csv"))
    person_name._overrides.cache_clear()


@pytest.mark.parametrize("lastname, firstname, expected", [
    ("Nguyễn Văn", "An", "Nguyễn Văn An"),            # đúng quy ước: giữ nguyên
    ("Trần Văn", "Thi", "Trần Văn Thi"),              # "Thi" là tên gọi, không phải chữ đệm "Thị"
    ("Lê", "Thiên Ân", "Lê Thiên Ân"),                # ô lastname một chữ nhưng đúng là họ
    ("Trần", "Nguyễn Văn Tú", "Trần Nguyễn Văn Tú"),  # họ ghép: không chắc nên giữ nguyên
    ("Hùng", "Siu", "Hùng Siu"),                      # không đoán với tên không theo khuôn họ Việt
    ("Minh", "Lê Hoàng", "Lê Hoàng Minh"),            # nhập ngược: firstname bắt đầu bằng họ
    ("Lan", "Phạm Thị", "Phạm Thị Lan"),              # firstname kết thúc bằng chữ đệm "Thị"
    ("Mai", "Đỗ Văn", "Đỗ Văn Mai"),                  # "Mai" vừa là họ vừa là tên, đứng một mình -> tên
    ("Trân", "Nguyễn Ngọc", "Nguyễn Ngọc Trân"),      # "Trân" có dấu khác họ "Trần"
    ("Binh", "Tran Van", "Tran Van Binh"),            # gõ không dấu vẫn nhận ra họ
])
def test_full_name_order(lastname, firstname, expected):
    assert full_name(lastname, firstname) == expected


def test_not_swapped_when_a_part_is_empty():
    assert not is_swapped("", "Nguyễn Văn")
    assert full_name(None, " An ") == "An"


def test_override_file_wins(monkeypatch, tmp_path):
    path = tmp_path / "ten.csv"
    path.write_text("user_id,ho_dem,ten\n7,Đặng Văn,Bình\n", encoding="utf-8")
    monkeypatch.setenv("LMS_NAME_OVERRIDES", str(path))
    person_name._overrides.cache_clear()
    assert full_name("Binh", "Dang Van", 7) == "Đặng Văn Bình"
    assert full_name("Binh", "Dang Van", 8) == "Dang Van Binh"
