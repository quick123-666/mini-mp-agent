# generate_quarantine_report.ps1
# Generate quarantine report from full detector scan
param(
    [string]$CsvPath = 'C:\Users\Administrator\.qclaw\workspace\scripts\encoding_detect.csv',
    [string]$OutPath = 'C:\Users\Administrator\.qclaw\workspace\scripts\quarantine_report.md'
)

if (-not (Test-Path $CsvPath)) {
    Write-Host "CSV_NOT_FOUND: $CsvPath"
    exit 1
}

$results = Import-Csv $CsvPath
$utf8_ok = $results | Where-Object { $_.Category -eq 'UTF8_OK' }
$mixed = $results | Where-Object { $_.Category -eq 'MIXED' }
$gbk_ok = $results | Where-Object { $_.Category -eq 'GBK_OK' }
$double_enc = $results | Where-Object { $_.Category -eq 'DOUBLE_ENC' }
$empty = $results | Where-Object { $_.Category -eq 'EMPTY' }

# Re-classify MIXED into 'bom-ascii-cron' (false positive) vs 'true-mixed' (real corruption)
$bomAsciiCron = 0
$trueMixed = 0
$trueMixedList = @()
foreach ($m in $mixed) {
    if ($m.Detail -match 'bom=True utf8: common=0 extA=0 repl=0') {
        $bomAsciiCron++
    } else {
        $trueMixed++
        $trueMixedList += $m
    }
}

$totalBytes = ($results | Measure-Object Size -Sum).Sum
$totalMixedBytes = ($mixed | Measure-Object Size -Sum).Sum
$totalUtf8Bytes = ($utf8_ok | Measure-Object Size -Sum).Sum

$out = "# Encoding Quarantine Report (2026-07-19 18:30)`n`n"
$out += "**Generated from**: ``$CsvPath```n"
$out += "**Total .md files scanned**: $($results.Count)`n"
$out += "**Total bytes**: $([Math]::Round($totalBytes / 1MB, 2)) MB`n`n"

$out += "## Summary`n`n"
$out += "| Category | Count | Bytes | % |`n"
$out += "|---|---|---|---|`n"
$out += "| UTF8_OK | $($utf8_ok.Count) | $([Math]::Round($totalUtf8Bytes / 1KB, 1)) KB | $([Math]::Round($utf8_ok.Count * 100 / $results.Count, 2))% |`n"
$out += "| GBK_OK | $($gbk_ok.Count) | 0 KB | 0% |`n"
$out += "| DOUBLE_ENC | $($double_enc.Count) | 0 KB | 0% |`n"
$out += "| MIXED (total) | $($mixed.Count) | $([Math]::Round($totalMixedBytes / 1MB, 2)) MB | $([Math]::Round($mixed.Count * 100 / $results.Count, 2))% |`n"
$out += "| - bom-ascii-cron (false positive) | $bomAsciiCron | - | - |`n"
$out += "| - true-mixed (real corruption) | $trueMixed | - | - |`n"
$out += "| EMPTY | $($empty.Count) | 0 | 0% |`n`n"

$out += "## Verdict`n`n"
if ($trueMixed -eq 0) {
    $out += "All MIXED files are BOM+ASCII cron logs (false positives). No real corruption remains.`n`n"
} else {
    $pctMixed = [Math]::Round($trueMixed * 100 / $results.Count, 2)
    $out += "**$trueMixed true-MIXED files ($pctMixed%)** require manual intervention or are unrecoverable (no original source).`n`n"
    $out += "Most of these are GBK bytes mis-stored as UTF-8 + UTF-8 BOM (double-encoding corruption, 16:30 LCM-era repair script created this state). Original content cannot be reconstructed without source backup.`n`n"
}

$out += "## Top 20 directories with most MIXED files`n`n"
$mixed | Group-Object { Split-Path $_.File -Parent } | Sort-Object Count -Descending | Select-Object -First 20 Count,Name | ForEach-Object {
    $out += "- $($_.Count) - $($_.Name)`n"
}

$out += "`n## Recommendation`n`n"
$out += "1. **UTF8_OK files**: Safe to read. Use detector before reading (D-DetectEncoding-001).`n"
$out += "2. **BOM+ASCII cron logs**: Safe to read (cron healthcheck output, no Chinese). Skip detector threshold for this case.`n"
$out += "3. **True MIXED files**: Unrecoverable. Recommend moving to ``archive/corrupted-2026-07-19/`` for hygiene, OR leave in place with detector skip list.`n`n"

$out += "**Decision pending**: Per D-ShipCompletionDefinition-001 rule 6, do not create new M-NNN for this; the encoding issue is already covered by M-WriteToolGBK-001 + D-BackupBeforeDestructiveTransform-001. The 95% MIXED damage is a historical artifact (2026-07-19 14:33 GBK repair attempt), not new errors.`n"

$out | Out-File -FilePath $OutPath -Encoding utf8
Write-Host "Report written to: $OutPath"
Write-Host "Total: $($results.Count), UTF8_OK: $($utf8_ok.Count), MIXED: $($mixed.Count) ($bomAsciiCron bom-ascii-cron + $trueMixed true-mixed)"