# Mở báo cáo bằng Microsoft Word: cập nhật mục lục / danh mục hình / danh mục bảng, lưu lại và xuất PDF.
#   powershell -ExecutionPolicy Bypass -File docs/bao_cao/finalize_word.ps1
$ErrorActionPreference = "Stop"
$docx = Join-Path $PSScriptRoot "BaoCao_PTTK_LMS_Analytics.docx"
$pdf = [System.IO.Path]::ChangeExtension($docx, ".pdf")

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx, $false, $false)
    # Cập nhật hai lần: lần đầu số trang của mục lục thay đổi độ dài phần đầu, lần hai cho số trang đúng
    for ($pass = 0; $pass -lt 2; $pass++) {
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        $doc.Fields.Update() | Out-Null
    }
    # Đoạn đóng trường cuối mỗi mục lục: thu nhỏ để không đẩy nội dung sang một trang trắng
    foreach ($toc in $doc.TablesOfContents) {
        $last = $toc.Range.Paragraphs.Last
        $last.Range.Font.Size = 1
        $last.SpaceAfter = 0
        $last.SpaceBefore = 0
        $last.LineSpacingRule = 4          # wdLineSpaceExactly
        $last.LineSpacing = 1
    }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)          # 17 = wdExportFormatPDF
    Write-Output ("Trang: " + $doc.ComputeStatistics(2))
    $doc.Close($false)
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
Write-Output "Đã cập nhật mục lục và xuất $pdf"
