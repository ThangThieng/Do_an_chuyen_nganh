import { Select } from "antd";

/**
 * Bộ lọc Năm học / Học kỳ / Khoa – một hàng phía trên nội dung mà nó áp dụng.
 * Dữ liệu chỉ có một khoa: ô "Khoa" (chỉ có "Tất cả khoa" và đúng một khoa) được thay bằng ô "Bộ môn / Chuyên ngành"
 * nếu trang truyền onDepartmentChange, không thì ẩn.
 */
export const isSingleFaculty = (filters) => (filters?.faculties ?? []).length === 1;

export default function TermFilterBar({ filters, term, onTermChange, facultyId, onFacultyChange, showFaculty = true,
  departmentId, onDepartmentChange }) {
  const years = filters?.academic_years ?? [];
  const single = isSingleFaculty(filters);
  return (
    <>
      <Select
        aria-label="Năm học"
        style={{ width: 180 }}
        value={term?.academic_year}
        onChange={(academic_year) => onTermChange({ ...term, academic_year })}
        options={years.map((y) => ({ value: y, label: `Năm học ${y}` }))}
      />
      <Select
        aria-label="Học kỳ"
        style={{ width: 120 }}
        value={term?.semester}
        onChange={(semester) => onTermChange({ ...term, semester })}
        options={[1, 2, 3].map((s) => ({ value: s, label: s === 3 ? "HK hè" : `HK${s}` }))}
      />
      {showFaculty && single && onDepartmentChange && (
        <Select
          aria-label="Bộ môn / Chuyên ngành"
          style={{ width: 280 }}
          value={departmentId ?? "ALL"}
          onChange={(v) => onDepartmentChange(v === "ALL" ? undefined : v)}
          options={[{ value: "ALL", label: `${filters.faculties[0].name}: tất cả bộ môn` },
            ...(filters?.departments ?? []).map((d) => ({ value: d.id, label: d.name }))]}
        />
      )}
      {showFaculty && !single && (
        <Select
          aria-label="Khoa"
          style={{ width: 240 }}
          value={facultyId ?? "ALL"}
          onChange={(v) => onFacultyChange(v === "ALL" ? undefined : v)}
          options={[{ value: "ALL", label: "Tất cả khoa" },
            ...(filters?.faculties ?? []).map((f) => ({ value: f.id, label: f.name }))]}
        />
      )}
    </>
  );
}
