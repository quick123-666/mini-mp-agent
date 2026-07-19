# check_method_classification.ps1
# Scan working-methods.md and MEMORY.md for D/M-NNN entries missing cat= field
# Returns: exit 0 if all OK, exit 1 if missing found
# Usage: pwsh -NoProfile -File check_method_classification.ps1 [-Silent]

param([switch]$Silent)

$workspace = 'C:\Users\Administrator\.qclaw\workspace'
$targets = @(
    "$workspace\skills\meta-planner\methods\working-methods.md",
    "$workspace\MEMORY.md"
)

$missing = @()
$total = 0

# Pattern: D-NNN-NNN or M-NNN-NNN (any of the dash-separated naming variants)
$idPattern = '\*\*(?:[DM])-[A-Za-z0-9]+-(?:\d{3}|[A-Za-z0-9]+)\*\*'
# Cat in same line or next line (within reasonable proximity)
$catPattern = '\[cat='

$reportLines = @()

foreach ($target in $targets) {
    if (-not (Test-Path $target)) {
        $reportLines += "FILE_NOT_FOUND: $target"
        continue
    }

    $content = Get-Content -Path $target -Encoding UTF8
    $inMethodBlock = $false
    $lastId = $null

    for ($i = 0; $i -lt $content.Count; $i++) {
        $line = $content[$i]

        # Match method/decision IDs like **D-ShipCompletionDefinition-001** or **M-LoopSizeControl-001**
        $idMatch = [regex]::Match($line, '\*\*(?<id>(?:[DM])-[A-Za-z0-9]+-(?:\d{3}|[A-Za-z0-9]+))\*\*')
        if ($idMatch.Success) {
            $total++
            $id = $idMatch.Groups['id'].Value

            # Check current line and next 2 lines for cat=
            $hasCat = $false
            for ($j = 0; $j -le 2 -and ($i + $j) -lt $content.Count; $j++) {
                if ($content[$i + $j] -match '\[cat=l[012]|\[cat=other') {
                    $hasCat = $true
                    break
                }
            }

            if (-not $hasCat) {
                $missing += @{
                    Id   = $id
                    File = $target
                    Line = $i + 1
                    Text = $line.Trim()
                }
            }
        }
    }
}

# Output
if ($missing.Count -eq 0) {
    if (-not $Silent) {
        Write-Host "METHOD_CLASSIFICATION_CHECK: PASS"
        Write-Host "Total D/M-NNN entries checked: $total"
        Write-Host "Missing cat=: 0"
    }
    exit 0
} else {
    if (-not $Silent) {
        Write-Host "METHOD_CLASSIFICATION_CHECK: FAIL"
        Write-Host "Total D/M-NNN entries: $total"
        Write-Host "Missing cat=: $($missing.Count)"
        Write-Host "`nMissing entries:"
        foreach ($m in $missing) {
            Write-Host "  $($m.Id) at $($m.File):$($m.Line)"
        }
    }
    exit 1
}