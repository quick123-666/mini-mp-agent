# repair_gbk_corruption.ps1
# Inline detector (avoids dot-source double-scan issue)
param(
    [Parameter(Mandatory=$true)] [string]$Path,
    [switch]$DryRun,
    [string]$QuarantineList = 'C:\Users\Administrator\.qclaw\workspace\scripts\quarantine.csv'
)

if (-not (Test-Path $Path)) {
    Write-Host "FILE_NOT_FOUND: $Path"
    exit 1
}

# Inline BOM test
function Test-Utf8Bom {
    param([byte[]]$b)
    return ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
}

# Inline Get-Category (only for 1 file, fast)
function Get-Category {
    param([byte[]]$b)
    if ($b.Length -eq 0) { return @{ Cat='EMPTY'; Detail='empty file' } }

    $hasBom = Test-Utf8Bom $b
    $body = if ($hasBom) { $b[3..($b.Length-1)] } else { $b }

    $utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
    $utf8Ok = $true
    $utf8Text = ''
    try { $utf8Text = $utf8Strict.GetString($body) } catch {
        $utf8Ok = $false
        $utf8Text = [System.Text.Encoding]::UTF8.GetString($body)
    }

    $gbk = [System.Text.Encoding]::GetEncoding('GBK')
    try { $gbkText = $gbk.GetString($body) } catch { $gbkText = '' }

    $basic = 0; $extA = 0; $repl = 0; $ascii = 0
    $sample = $utf8Text.Substring(0, [Math]::Min(2000, $utf8Text.Length))
    $commonHits = 0
    $commonCodes = @(0x5DE5,0x4F5C,0x65B9,0x6CD5,0x8BB0,0x5FC6,0x539F,0x5219,0x5B50,0x63A5,0x5165,0x9700,0x6C42,0x53E3,0x7AEF,0x7528,0x6237,0x67E5,0x770B,0x4EE3,0x7801)
    $commonSet = @{}
    foreach ($c in $commonCodes) { $commonSet[$c] = $true }
    foreach ($ch in $sample.ToCharArray()) {
        $cp = [int][char]$ch
        if ($cp -eq 0xFFFD) { $repl++ }
        elseif ($cp -lt 0x80) { $ascii++ }
        elseif ($cp -ge 0x4E00 -and $cp -le 0x9FFF) { $basic++ }
        elseif ($cp -ge 0x3400 -and $cp -le 0x4DFF) { $extA++ }
        if ($commonSet.ContainsKey($cp)) { $commonHits++ }
    }
    $totalCjk = $basic + $extA
    $extARatio = if ($totalCjk -gt 0) { $extA / $totalCjk } else { 0 }
    $commonRatio = if ($sample.Length -gt 0) { $commonHits / $sample.Length } else { 0 }
    $replRatio = if ($sample.Length -gt 0) { $repl / $sample.Length } else { 0 }

    $gbkBasic = 0; $gbkRepl = 0; $gbkCommon = 0
    $gsample = $gbkText.Substring(0, [Math]::Min(2000, $gbkText.Length))
    foreach ($ch in $gsample.ToCharArray()) {
        $cp = [int][char]$ch
        if ($cp -eq 0xFFFD) { $gbkRepl++ }
        elseif ($cp -ge 0x4E00 -and $cp -le 0x9FFF) { $gbkBasic++ }
        if ($commonSet.ContainsKey($cp)) { $gbkCommon++ }
    }
    $gbkTotal = $gbkBasic
    $gbkCommonRatio = if ($gsample.Length -gt 0) { $gbkCommon / $gsample.Length } else { 0 }

    if ($hasBom -and $utf8Ok -and $commonRatio -ge 0.005 -and $extARatio -lt 0.05) {
        return @{ Cat='UTF8_OK'; Detail="bom+utf8, common=$([Math]::Round($commonRatio,3)) extA=$([Math]::Round($extARatio,3))" }
    }
    if (-not $hasBom -and $commonRatio -ge 0.005 -and $extARatio -lt 0.05) {
        return @{ Cat='UTF8_OK'; Detail="no-bom utf8, common=$([Math]::Round($commonRatio,3)) extA=$([Math]::Round($extARatio,3))" }
    }
    if (-not $hasBom -and $gbkRepl -lt 5 -and $gbkCommonRatio -ge 0.005) {
        return @{ Cat='GBK_OK'; Detail="no-bom, gbkCommon=$([Math]::Round($gbkCommonRatio,3))" }
    }
    if ($hasBom -and $commonRatio -lt 0.001 -and $gbkCommonRatio -ge 0.005 -and $gbkRepl -lt 5) {
        return @{ Cat='DOUBLE_ENC'; Detail="bom+corrupt utf8: common=$([Math]::Round($commonRatio,3)) | gbk: common=$([Math]::Round($gbkCommonRatio,3))" }
    }
    return @{ Cat='MIXED'; Detail="bom=$hasBom utf8: common=$([Math]::Round($commonRatio,3)) extA=$([Math]::Round($extARatio,3)) repl=$([Math]::Round($replRatio,3)) | gbk: common=$([Math]::Round($gbkCommonRatio,3)) extA=0 repl=$gbkRepl" }
}

$bytes = [System.IO.File]::ReadAllBytes($Path)
$r = Get-Category $bytes
$category = $r.Cat
$detail = $r.Detail

Write-Host "FILE: $Path"
Write-Host "CATEGORY: $category"
Write-Host "DETAIL: $detail"

if ($category -eq 'UTF8_OK') {
    Write-Host "OK: no repair needed"
    exit 0
}

if ($category -eq 'EMPTY') {
    Write-Host "SKIP: empty file"
    exit 0
}

# Special case: BOM + UTF-8 + no Chinese (e.g. cron logs)
$bomMatch = ($detail -match 'bom=True') -or ($detail -match 'bom=True')
$noRepl = $detail -match 'repl=0'
if ($category -eq 'MIXED' -and $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF -and $noRepl) {
    Write-Host "OK: BOM + UTF-8 + no replacement chars (likely cron log / ASCII content)"
    exit 0
}

# MIXED/DOUBLE_ENC/GBK_OK: try GBK -> UTF-8 repair
$gbk = [System.Text.Encoding]::GetEncoding('GBK')
try {
    $str = $gbk.GetString($bytes)
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $newBytes = $utf8.GetBytes($str)

    $commonBytes = New-Object System.Collections.ArrayList
    $commonBytes.Add(@(0xE7,0x9A,0x84)) | Out-Null
    $commonBytes.Add(@(0xE6,0x98,0xAF)) | Out-Null
    $commonBytes.Add(@(0xE5,0x9C,0xA8)) | Out-Null
    $commonBytes.Add(@(0xE4,0xBA,0x86)) | Out-Null
    $commonBytes.Add(@(0xE5,0x92,0x8C)) | Out-Null
    $commonBytes.Add(@(0xE6,0x9C,0x89)) | Out-Null
    $commonBytes.Add(@(0xE6,0x88,0x91)) | Out-Null
    $commonBytes.Add(@(0xE4,0xBD,0xA0)) | Out-Null
    $commonBytes.Add(@(0xE4,0xBB,0x96)) | Out-Null
    $commonBytes.Add(@(0xE5,0xA5,0xB9)) | Out-Null
    $commonBytes.Add(@(0xE4,0xBB,0xAC)) | Out-Null
    $commonBytes.Add(@(0xE4,0xB8,0xAD)) | Out-Null
    $commonBytes.Add(@(0xE5,0xA4,0xA7)) | Out-Null
    $commonBytes.Add(@(0xE4,0xB8,0xBA)) | Out-Null
    $commonBytes.Add(@(0xE4,0xB8,0x8A)) | Out-Null
    $commonBytes.Add(@(0xE5,0x9B,0xBD)) | Out-Null
    $commonBytes.Add(@(0xE5,0xAD,0xA6)) | Out-Null
    $commonBytes.Add(@(0xE7,0x94,0x9F)) | Out-Null
    $commonBytes.Add(@(0xE6,0x97,0xB6)) | Out-Null

    $commonHits = 0
    foreach ($c in $commonBytes) {
        $hits = 0
        for ($i = 0; ($i + 2) -lt $newBytes.Length; $i++) {
            if ($newBytes[$i] -eq $c[0] -and $newBytes[$i+1] -eq $c[1] -and $newBytes[$i+2] -eq $c[2]) {
                $hits++
                $i += 2
            }
        }
        $commonHits += $hits
    }

    Write-Host "TRY-REPAIR: GBK decode successful, commonHits=$commonHits"
    if ($commonHits -ge 1) {
        if ($DryRun) {
            Write-Host "DRY-RUN: would write UTF-8 no-BOM"
        } else {
            [System.IO.File]::WriteAllBytes($Path, $newBytes)
            Write-Host "REPAIRED: wrote UTF-8 no-BOM"
        }
        exit 0
    } else {
        Write-Host "FAIL: commonHits=$commonHits < 1, marking as quarantine"
    }
} catch {
    Write-Host "FAIL: GBK decode error: $($_.Exception.Message)"
}

$quarantineEntry = "$Path`t$category`t$detail"
Add-Content -Path $QuarantineList -Value $quarantineEntry -Encoding utf8
Write-Host "QUARANTINE: appended to $QuarantineList"
exit 1