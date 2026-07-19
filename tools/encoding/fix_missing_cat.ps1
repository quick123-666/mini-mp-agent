# fix_missing_cat.ps1
# Batch-fix missing cat= in working-methods.md based on section headers
# Backup already created as working-methods.md.bak

$path = 'C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\methods\working-methods.md'
$content = Get-Content -Path $path -Encoding UTF8

# Map section headers to cat=
$sectionCat = @{}
$currentCat = 'other'  # default for unclassified sections

$fixed = 0
$output = @()

for ($i = 0; $i -lt $content.Count; $i++) {
    $line = $content[$i]

    # Detect section header → set current cat
    if ($line -match '^##\s+\d+\.\s.+\(l0,') { $currentCat = 'l0' }
    elseif ($line -match '^##\s+\d+\.\s.+\(l1[),]') { $currentCat = 'l1' }
    elseif ($line -match '^##\s+\d+\.\s.+\(l2[),]') { $currentCat = 'l2' }
    elseif ($line -match '^##\s+\d+\.\s.+\(other[),]') { $currentCat = 'other' }
    elseif ($line -match '^##\s+\d+\.\s+') { $currentCat = 'other' }  # default

    # Match method/decision ID lines
    $idMatch = [regex]::Match($line, '\*\*(?<id>(?:[DM])-[A-Za-z0-9]+-(?:\d{3}|[A-Za-z0-9]+))\*\*')
    if (-not $idMatch.Success) {
        $output += $line
        continue
    }

    # Check if this line (or next 2) already has cat=
    $hasCat = $false
    for ($j = 0; $j -le 2 -and ($i + $j) -lt $content.Count; $j++) {
        if ($content[$i + $j] -match '\[cat=l[012]|\[cat=other') {
            $hasCat = $true
            break
        }
    }

    if (-not $hasCat) {
        # Insert cat= after the ID on the same line
        # Pattern: **M-XXX-001** — description text
        $newLine = $line -replace '(\*\*(?:[DM])-[A-Za-z0-9]+-(?:\d{3}|[A-Za-z0-9]+)\*\*)', "`$1 [cat=$currentCat]"
        if ($newLine -ne $line) {
            $output += $newLine
            $fixed++
        } else {
            $output += $line
        }
    } else {
        $output += $line
    }
}

Write-Host "Fixed: $fixed entries (added cat= based on section)"
$output | Out-File -FilePath $path -Encoding UTF8
Write-Host "Done"