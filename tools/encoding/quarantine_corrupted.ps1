# quarantine_corrupted.ps1
# Copy 31 true-MIXED files to archive/corrupted-2026-07-19/ for hygiene
# Originals remain in place (do not delete - user content has value)
param(
    [string]$CsvPath = 'C:\Users\Administrator\.qclaw\workspace\scripts\encoding_detect.csv',
    [string]$ArchiveRoot = 'C:\Users\Administrator\.qclaw\workspace\archive\corrupted-2026-07-19'
)

if (-not (Test-Path $CsvPath)) {
    Write-Host "CSV_NOT_FOUND: $CsvPath"
    exit 1
}

if (-not (Test-Path $ArchiveRoot)) {
    New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
}

$results = Import-Csv $CsvPath
$trueMixed = $results | Where-Object { $_.Category -eq 'MIXED' -and $_.Detail -notmatch 'bom=True utf8: common=0 extA=0 repl=0' }

$copied = 0
$skipped = 0
$log = "Quarantine log (2026-07-19 18:35):`n`n"

foreach ($f in $trueMixed) {
    $src = $f.File
    if (-not (Test-Path $src)) {
        $skipped++
        $log += "SKIP (not found): $src`n"
        continue
    }

    # Compute relative path under workspace
    $rel = $src.Replace('C:\Users\Administrator\.qclaw\workspace\', '')
    $dst = Join-Path $ArchiveRoot $rel
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }

    Copy-Item -Path $src -Destination $dst -Force
    $copied++
    $log += "COPIED: $src -> $dst`n"
}

$log += "`nSummary: copied=$copied, skipped=$skipped`n"

$log | Out-File -FilePath 'C:\Users\Administrator\.qclaw\workspace\scripts\quarantine_log.txt' -Encoding utf8
Write-Host "Quarantine log written to scripts\quarantine_log.txt"
Write-Host "Summary: copied=$copied, skipped=$skipped"
Write-Host "Archive root: $ArchiveRoot"