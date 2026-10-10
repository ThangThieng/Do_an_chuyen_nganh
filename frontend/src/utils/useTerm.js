/**
 * Học kỳ đang xem lưu trên URL (?ay=2026-2027&sem=1) để F5, nút Back và chia sẻ đường dẫn giữ đúng học kỳ khi đi
 * qua các cấp Toàn trường › Khoa › Môn học (góp ý 3). Không có trên URL thì dùng học kỳ của dữ liệu mới nhất.
 */
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useFilters } from "../api/hooks.js";

export default function useTerm() {
  const [params, setParams] = useSearchParams();
  const { data: filters } = useFilters();
  const ay = params.get("ay");
  const sem = Number(params.get("sem")) || null;
  const term = useMemo(() => {
    if (ay && sem) return { academic_year: ay, semester: sem };
    return filters?.current ?? null;
  }, [ay, sem, filters]);
  const setTerm = useCallback((next) => {
    setParams((prev) => {
      const p = new URLSearchParams(prev);
      if (next?.academic_year) p.set("ay", next.academic_year);
      if (next?.semester) p.set("sem", String(next.semester));
      return p;
    }, { replace: true });
  }, [setParams]);
  const search = term ? `?ay=${encodeURIComponent(term.academic_year)}&sem=${term.semester}` : "";
  return { term, setTerm, search, filters };
}
