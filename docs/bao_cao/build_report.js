/**
 * Dựng báo cáo Word từ các file nội dung docs/bao_cao/noi_dung/*.md (cú pháp đánh dấu rút gọn).
 *
 *   node docs/bao_cao/build_report.js            -> docs/bao_cao/BaoCao_PTTK_LMS_Analytics.docx
 *
 * Cú pháp:
 *   # / ## / ### / ####      tiêu đề cấp 1–4 (cấp 1 luôn sang trang mới)
 *   - mục                     danh sách gạch đầu dòng;   1. mục   danh sách đánh số (mỗi danh sách đánh số lại từ 1)
 *   Bảng: chú thích           chú thích cho bảng ngay sau; dòng "%w 10,30,60" đặt tỉ lệ độ rộng cột
 *   | a | b |                 bảng (dòng đầu là tiêu đề); "<br>" xuống dòng trong ô
 *   ![chú thích](đường/dẫn.png){w=15}   hình, rộng 15 cm (mặc định 16 cm), chú thích đánh số theo chương
 *   **đậm**, *nghiêng*, `mã`  định dạng trong dòng
 *   [[TOC]] [[LOF]] [[LOT]]   mục lục, danh mục hình, danh mục bảng;  \newpage  sang trang
 */
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun, LevelFormat, Packer, PageBreak,
  PageNumber, Paragraph, ShadingType, Table, TableCell, TableOfContents, TableRow, TextRun, WidthType,
  NumberFormat, VerticalAlign, TabStopType, TabStopPosition, PageOrientation,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const SRC = path.join(__dirname, "noi_dung");
const OUT = path.join(__dirname, "BaoCao_PTTK_LMS_Analytics.docx");
const FONT = "Times New Roman";
const PAGE = { width: 11906, height: 16838, top: 1134, bottom: 1134, left: 1701, right: 1134 };
const CONTENT_W = PAGE.width - PAGE.left - PAGE.right;           // 9071 DXA
const CONTENT_PX = Math.round(CONTENT_W / 1440 * 96);           // ~605 px
const MAX_IMG_H_PX = Math.round(22 / 2.54 * 96);                // ảnh cao tối đa 22 cm
// Trang ngang ([[NGANG]] ... [[/NGANG]]) cho sơ đồ lớn: rộng ~24,7 cm, ảnh cao tối đa 15 cm
const LANDSCAPE_PX = Math.round((PAGE.height - PAGE.left - PAGE.right) / 1440 * 96);
const MAX_IMG_H_LANDSCAPE_PX = Math.round(15 / 2.54 * 96);
let landscape = false;

// ----------------------------------------------------------------------------- định dạng trong dòng
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: (base.size ?? 26) - 4, ...base, bold: base.bold }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

// ----------------------------------------------------------------------------- ảnh
function pngSize(file) {
  const buf = fs.readFileSync(file);
  return { buf, w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

// ----------------------------------------------------------------------------- danh sách đánh số
const numberingConfigs = [{
  reference: "bullets",
  levels: [{ level: 0, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
  { level: 1, format: LevelFormat.BULLET, text: "+", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }],
}];
let listCounter = 0;
function newNumberedList() {
  const reference = `num-${++listCounter}`;
  numberingConfigs.push({
    reference,
    levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
  });
  return reference;
}

// ----------------------------------------------------------------------------- bảng
const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: border, bottom: border, left: border, right: border };

function cellParagraphs(text, header) {
  return text.split(/<br\s*\/?>/i).map((part) => {
    const trimmed = part.trim();
    const bullet = trimmed.startsWith("• ");
    return new Paragraph({
      spacing: { before: 20, after: 20, line: 264 },
      alignment: header ? AlignmentType.CENTER : AlignmentType.LEFT,
      indent: bullet ? { left: 180, hanging: 180 } : undefined,
      children: runs(trimmed, { size: 22, bold: header || undefined, font: FONT }),
    });
  });
}

function buildTable(rows, widths) {
  const cols = rows[0].length;
  let pct = widths && widths.length === cols ? widths : Array(cols).fill(100 / cols);
  const sum = pct.reduce((a, b) => a + b, 0);
  let dxa = pct.map((p) => Math.floor(p / sum * CONTENT_W));
  dxa[dxa.length - 1] += CONTENT_W - dxa.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: dxa,
    rows: rows.map((cells, r) => new TableRow({
      tableHeader: r === 0,
      cantSplit: false,
      children: cells.map((c, i) => new TableCell({
        borders,
        width: { size: dxa[i], type: WidthType.DXA },
        shading: r === 0 ? { fill: "E3E8EF", type: ShadingType.CLEAR, color: "auto" } : undefined,
        margins: { top: 50, bottom: 50, left: 90, right: 90 },
        verticalAlign: VerticalAlign.CENTER,
        children: cellParagraphs(c, r === 0),
      })),
    })),
  });
}

// ----------------------------------------------------------------------------- chuyển nội dung
function convert(text) {
  const blocks = [];
  const lines = text.replace(/\r/g, "").split("\n");
  let chapter = 0;
  let fig = 0;
  let tab = 0;
  let pendingCaption = null;
  let pendingWidths = null;
  let numberedRef = null;
  let i = 0;

  const para = (t, opts = {}) => new Paragraph({
    alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 312 }, indent: { firstLine: 567 },
    children: runs(t), ...opts,
  });

  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (!t) { numberedRef = null; i++; continue; }

    if (t.startsWith("@@ ")) {       // tiêu đề trang không đánh số, không vào mục lục
      // Đoạn ngắt trang cao 1pt: tránh bị đẩy sang trang mới (sinh trang trắng) khi trang trước vừa kín
      if (blocks.length > 0) blocks.push(new Paragraph({ spacing: { before: 0, after: 0, line: 20, lineRule: "exact" },
        children: [new TextRun({ size: 2 }), new PageBreak()] }));
      blocks.push(new Paragraph({ alignment: AlignmentType.CENTER,
        spacing: { after: 360 }, children: [new TextRun({ text: t.slice(3), bold: true, size: 32 })] }));
      i++; continue;
    }
    if (t === "[[NGANG]]" || t === "[[/NGANG]]") {
      landscape = t === "[[NGANG]]";
      blocks.push({ __section: landscape ? "landscape" : "portrait" });
      i++; continue;
    }
    if (t === "[[DOTLINE]]") {       // dòng chấm kín bề rộng trang (trang nhận xét)
      blocks.push(new Paragraph({ spacing: { after: 0, line: 480 },
        tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W, leader: "dot" }],
        children: [new TextRun({ text: "\t" })] }));
      i++; continue;
    }
    if (t === "\\newpage") { blocks.push(new Paragraph({ children: [new PageBreak()] })); i++; continue; }
    if (t === "[[TOC]]") {
      blocks.push(new TableOfContents("Mục lục", { hyperlink: true, headingStyleRange: "1-3" }));
      i++; continue;
    }
    if (t === "[[LOF]]" || t === "[[LOT]]") {
      const style = t === "[[LOF]]" ? "ChuThichHinh" : "ChuThichBang";
      blocks.push(new TableOfContents(t === "[[LOF]]" ? "Danh mục hình" : "Danh mục bảng",
        { hyperlink: true, stylesWithLevels: [{ styleName: style, level: 1 }] }));
      i++; continue;
    }

    const h = /^(#{1,4})\s+(.*)$/.exec(t);
    if (h) {
      const level = h[1].length;
      if (level === 1) {
        const cm = /^CHƯƠNG\s+(\d+)/i.exec(h[2]);
        if (cm) { chapter = Number(cm[1]); fig = 0; tab = 0; }
      }
      blocks.push(new Paragraph({
        heading: [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3, HeadingLevel.HEADING_4][level - 1],
        pageBreakBefore: level === 1,
        children: runs(h[2]),
      }));
      i++; continue;
    }

    if (t.startsWith("Bảng:")) { pendingCaption = t.slice(5).trim(); i++; continue; }
    if (t.startsWith("%w ")) { pendingWidths = t.slice(3).split(",").map(Number); i++; continue; }

    if (t.startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        const row = lines[i].trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
        if (!row.every((c) => /^:?-{2,}:?$/.test(c))) rows.push(row);
        i++;
      }
      if (pendingCaption) {
        tab += 1;
        blocks.push(new Paragraph({ style: "ChuThichBang", keepNext: true,
          children: [new TextRun({ text: `Bảng ${chapter}.${tab}. `, bold: true }), ...runs(pendingCaption)] }));
      }
      blocks.push(buildTable(rows, pendingWidths));
      blocks.push(new Paragraph({ spacing: { after: 60 }, children: [] }));
      pendingCaption = null; pendingWidths = null;
      continue;
    }

    const img = /^!\[(.*)\]\((.+?)\)(\{w=([\d.]+)\})?$/.exec(t);
    if (img) {
      const file = path.resolve(ROOT, img[2]);
      const { buf, w, h: hh } = pngSize(file);
      const maxW = landscape ? LANDSCAPE_PX : CONTENT_PX;
      const maxH = landscape ? MAX_IMG_H_LANDSCAPE_PX : MAX_IMG_H_PX;
      let width = img[4] ? Math.round(Number(img[4]) / 2.54 * 96) : maxW;
      width = Math.min(width, maxW);
      let height = Math.round(width * hh / w);
      if (height > maxH) { width = Math.round(width * maxH / height); height = maxH; }
      blocks.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
        children: [new ImageRun({ type: "png", data: buf, transformation: { width, height } })] }));
      fig += 1;
      blocks.push(new Paragraph({ style: "ChuThichHinh",
        children: [new TextRun({ text: `Hình ${chapter}.${fig}. `, bold: true }), ...runs(img[1])] }));
      i++; continue;
    }

    const bullet = /^(\s*)-\s+(.*)$/.exec(line);
    if (bullet) {
      blocks.push(new Paragraph({ numbering: { reference: "bullets", level: bullet[1].length >= 2 ? 1 : 0 },
        alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 312 }, children: runs(bullet[2]) }));
      i++; continue;
    }
    const num = /^\d+\.\s+(.*)$/.exec(t);
    if (num) {
      if (!numberedRef) numberedRef = newNumberedList();
      blocks.push(new Paragraph({ numbering: { reference: numberedRef, level: 0 },
        alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 312 }, children: runs(num[1]) }));
      i++; continue;
    }

    // Đoạn văn: gộp các dòng liền nhau
    const buf = [t];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#|\||- |\d+\. |!\[|Bảng:|%w |\\newpage|\[\[)/.test(lines[i].trim())) {
      buf.push(lines[i].trim()); i++;
    }
    const joined = buf.join(" ");
    if (joined.startsWith(">> ")) blocks.push(para(joined.slice(3), { indent: { left: 567 }, children: runs(joined.slice(3), { italics: true }) }));
    else blocks.push(para(joined));
  }
  return blocks;
}

// ----------------------------------------------------------------------------- trang bìa
function cover() {
  const meta = JSON.parse(fs.readFileSync(path.join(SRC, "bia.json"), "utf8"));
  const c = (text, size, opts = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
    children: [new TextRun({ text, size, font: FONT, ...opts })], ...(opts.p ?? {}) });
  const members = meta.members.map((m) => new Paragraph({
    tabStops: [{ type: TabStopType.LEFT, position: 3600 }, { type: TabStopType.LEFT, position: 6600 }],
    spacing: { after: 60 },
    children: [new TextRun({ text: `\t${m.name}`, size: 26 }), new TextRun({ text: `\t${m.id}`, size: 26 })],
  }));
  return [
    c(meta.university.toUpperCase(), 28, { bold: true }),
    c(meta.faculty.toUpperCase(), 28, { bold: true }),
    c("———————————", 26),
    new Paragraph({ spacing: { before: 1400 }, children: [] }),
    c(meta.kind.toUpperCase(), 30, { bold: true }),
    c(meta.subject.toUpperCase(), 28, { bold: true }),
    new Paragraph({ spacing: { before: 600 }, children: [] }),
    c("ĐỀ TÀI", 28, { bold: true }),
    ...meta.title.map((line) => c(line.toUpperCase(), 34, { bold: true, color: "1F3864" })),
    new Paragraph({ spacing: { before: 1200 }, children: [] }),
    new Paragraph({ tabStops: [{ type: TabStopType.LEFT, position: 3600 }], spacing: { after: 60 },
      children: [new TextRun({ text: "Giảng viên hướng dẫn:", size: 26, bold: true }), new TextRun({ text: `\t${meta.advisor}`, size: 26 })] }),
    new Paragraph({ tabStops: [{ type: TabStopType.LEFT, position: 3600 }], spacing: { after: 60 },
      children: [new TextRun({ text: "Lớp:", size: 26, bold: true }), new TextRun({ text: `\t${meta.class}`, size: 26 })] }),
    new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Sinh viên thực hiện:", size: 26, bold: true })] }),
    ...members,
    new Paragraph({ spacing: { before: 1600 }, children: [] }),
    c(meta.place_date, 26, { italics: true }),
  ];
}

// ----------------------------------------------------------------------------- tài liệu
const files = fs.readdirSync(SRC).filter((f) => f.endsWith(".md")).sort();
const front = [];
const body = [];
for (const f of files) {
  const blocks = convert(fs.readFileSync(path.join(SRC, f), "utf8"));
  (f.startsWith("00") ? front : body).push(...blocks);
}

const pageFooter = (fmt) => new Footer({
  children: [new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT], size: 24 })] })],
});
const pageProps = (extra = {}) => ({
  page: { size: { width: PAGE.width, height: PAGE.height },
    margin: { top: PAGE.top, bottom: PAGE.bottom, left: PAGE.left, right: PAGE.right }, ...extra },
});

/** Tách phần thân thành các section dọc/ngang theo dấu [[NGANG]]; số trang đánh liên tục từ 1. */
function bodySections() {
  const chunks = [{ orientation: "portrait", children: [] }];
  for (const b of body) {
    if (b && b.__section) chunks.push({ orientation: b.__section, children: [] });
    else chunks[chunks.length - 1].children.push(b);
  }
  return chunks.filter((c) => c.children.length).map((c, idx) => {
    const page = { ...pageProps().page };
    if (c.orientation === "landscape") page.size = { width: PAGE.width, height: PAGE.height, orientation: PageOrientation.LANDSCAPE };
    if (idx === 0) page.pageNumbers = { start: 1, formatType: NumberFormat.DECIMAL };
    return { properties: { page }, footers: { default: pageFooter() }, children: c.children };
  });
}

const doc = new Document({
  creator: "Nhóm thực hiện đồ án LMS Analytics",
  title: "Báo cáo Phân tích và thiết kế phần mềm – Hệ thống trực quan hóa dữ liệu LMS Moodle",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 26 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: "000000" },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "000000" },
        paragraph: { spacing: { before: 280, after: 140 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: "000000" },
        paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 2 } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, italics: true, font: FONT, color: "000000" },
        paragraph: { spacing: { before: 160, after: 80 }, keepNext: true, outlineLevel: 3 } },
      { id: "ChuThichHinh", name: "ChuThichHinh", basedOn: "Normal", next: "Normal",
        run: { size: 24, italics: true, font: FONT },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 } } },
      { id: "ChuThichBang", name: "ChuThichBang", basedOn: "Normal", next: "Normal",
        run: { size: 24, italics: true, font: FONT },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 160, after: 80 } } },
    ],
  },
  numbering: { config: numberingConfigs },
  sections: [
    { properties: pageProps(), children: cover() },
    { properties: { ...pageProps(), page: { ...pageProps().page, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } } },
      footers: { default: pageFooter() }, children: front },
    ...bodySections(),
  ],
});

Packer.toBuffer(doc).then(async (raw) => {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(raw);
  let xml = await zip.file("word/document.xml").async("string");
  xml = xml.replace(/<w:pgNumType w:start="1"\/>/g, '<w:pgNumType w:fmt="decimal" w:start="1"/>');
  zip.file("word/document.xml", xml);
  const b = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  fs.writeFileSync(OUT, b);
  console.log(`Đã ghi ${OUT} (${(b.length / 1048576).toFixed(1)} MB)`);
});
