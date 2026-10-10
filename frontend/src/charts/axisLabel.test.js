import { describe, expect, it } from "vitest";
import { axisLabel } from "./ComparisonCharts.jsx";

describe("axisLabel – nhãn trục cột dọc", () => {
  it("bỏ tiền tố 'Khoa' và ngắt tên dài thành nhiều dòng <= 14 ký tự", () => {
    const lines = axisLabel("Khoa Kinh tế – Quản trị kinh doanh", false);
    expect(lines).toEqual(["Kinh tế – Quản", "trị kinh doanh"]);
    for (const l of lines) expect(l.length).toBeLessThanOrEqual(14);
  });
  it("tên ngắn giữ một dòng; thanh ngang giữ nguyên tên đầy đủ", () => {
    expect(axisLabel("Khoa Luật", false)).toBe("Luật");
    expect(axisLabel("Khoa Kinh tế – Quản trị kinh doanh", true)).toBe("Khoa Kinh tế – Quản trị kinh doanh");
  });
});
