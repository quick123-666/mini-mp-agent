# t3_healthcheck.ps1
# T3 Daily Health Check — runs encoding + method classification + system health
# Usage: pwsh -NoProfile -File t3_healthcheck.ps1
# Exit 0 = PASS (silent), Exit 1 = FAIL (announced via cron failureAlert)

$workspace = 'C:\Users\Administrator\.qclaw\workspace'
$failures = @()
$warnings = @()

# ── Check 1: Encoding spot-check ──
$dirs = @("$workspace\skills\meta-planner\methods", "$workspace\memory")
$bad = 0; $total = 0
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Get-ChildItem $dir -Filter '*.md' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 50 | ForEach-Object {
            $total++
            $txt = [Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($_.FullName))
            if ($txt -match "\uFFFD") { $bad++ }
        }
    }
}
$ratio = if ($total -gt 0) { [math]::Round(100 * ($total - $bad) / $total, 1) } else { 100 }
if ($ratio -lt 50) { $failures += "Encoding: $ratio% clean ($bad/$total bad)" }
elseif ($ratio -lt 90) { $warnings += "Encoding: $ratio% clean ($bad/$total bad)" }

# ── Check 2: Method Classification ──
$check = "$workspace\scripts\check_method_classification.ps1"
$cResult = & powershell -NoProfile -ExecutionPolicy Bypass -NoLogo -File $check 2>&1
$cExit = $LASTEXITCODE
if ($cExit -ne 0) { $failures += "Method Classification: $cResult" }

# ── Check 3: working-methods.md ──
$wm = "$workspace\skills\meta-planner\methods\working-methods.md"
if (-not (Test-Path $wm)) { $failures += "working-methods.md: MISSING" }
else {
    $wmText = [Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($wm))
    $lines = ($wmText -split "`n").Count
    if (-not ($wmText -match 'Reconstructed')) { $warnings += "working-methods.md: $lines lines, missing Reconstructed banner" }
}

# ── Check 4: SOUL.md ──
$soul = "$workspace\SOUL.md"
if (-not (Test-Path $soul)) { $failures += "SOUL.md: MISSING" }
else {
    $soulText = [Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($soul))
    if ($soulText -match "\uFFFD") { $failures += "SOUL.md: contains U+FFFD (corrupted)" }
    elseif (-not ($soulText -match 'meta-planner')) { $warnings += "SOUL.md: missing meta-planner marker" }
}

# ── Check 5: HEARTBEAT.md ──
$hb = "$workspace\HEARTBEAT.md"
if (-not (Test-Path $hb)) { $warnings += "HEARTBEAT.md: MISSING" }
else {
    $hbText = [Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($hb))
    if ($hbText -match "\uFFFD") { $failures += "HEARTBEAT.md: corrupted" }
}

# ── Report ──
if ($failures.Count -gt 0) {
    Write-Host "T3_HEALTHCHECK: FAIL ($($failures.Count) fail, $($warnings.Count) warn)"
    foreach ($f in $failures) { Write-Host "  FAIL: $f" }
    foreach ($w in $warnings) { Write-Host "  WARN: $w" }
    exit 1
} else {
    Write-Host "T3_HEALTHCHECK: PASS ($($warnings.Count) warnings)"
    foreach ($w in $warnings) { Write-Host "  WARN: $w" }
    exit 0
}