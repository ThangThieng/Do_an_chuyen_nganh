import { describe, expect, it } from "vitest";
import { operationHints } from "./TrafficHeatmap.jsx";

// Ma trận 7 × 24: ban ngày (8–17h) đông, ban đêm vắng; Thứ 5 lúc 14h đông nhất; Chủ nhật 2–4h vắng nhất.
function matrix() {
  const cells = [];
  for (let d = 1; d <= 7; d += 1) {
    for (let h = 0; h < 24; h += 1) {
      let online = h >= 8 && h <= 17 ? 10 : 1;
      if (d === 5 && h === 14) online = 30;
      if (d === 7 && h >= 2 && h <= 4) online = 0;
      cells.push({ day_of_week: d, hour_of_day: h, avg_online_users: online, max_peak_online: online * 2 });
    }
  }
  return cells;
}

describe("operationHints – gợi ý giờ bảo trì / giám sát", () => {
  it("khung vắng nhất là 3 giờ liền nhau ít người online nhất, mỗi thứ một khung", () => {
    const { quiet } = operationHints(matrix());
    expect(quiet[0]).toMatchObject({ day: 7, start: 2, avg: 0 });
    expect(new Set(quiet.map((w) => w.day)).size).toBe(quiet.length);
    expect(quiet).toHaveLength(3);
  });

  it("giờ đông nhất xếp theo số người online trung bình, kèm đỉnh cao nhất", () => {
    const { busy } = operationHints(matrix());
    expect(busy[0]).toMatchObject({ day: 5, start: 14, avg: 30, peak: 60 });
  });

  it("ma trận rỗng không gợi ý gì", () => {
    expect(operationHints([])).toEqual({ quiet: [], busy: [] });
  });
});
