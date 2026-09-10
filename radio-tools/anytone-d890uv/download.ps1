# Downloads the Anytone AT-D890UV CPS/firmware packages referenced in
# docs/at-d890uv-programming.md. Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File radio-tools\anytone-d890uv\download.ps1
$ErrorActionPreference = "Stop"
$dest = Join-Path $PSScriptRoot "."
$items = @(
    @{ name = "D890UV_V1.05_official_260521.zip"; url = "https://anytoneusa.com/Files/D890UV%20V1.05%20DMR%20official%20release%20260521.zip" },
    @{ name = "D890UV_V1.05_NX_DMR_FW.zip";       url = "http://www.wouxun.us/Software/AnyTone-Software/D890UV_V1.05_NX_DMR_FW.zip" },
    @{ name = "D890UV-NR-board-reactivate.zip";   url = "http://www.wouxun.us/Software/AnyTone-Software/D890UV-NR-board-reactivate.zip" },
    @{ name = "Firmware-Update-Tool.zip";         url = "http://wouxun.us/Software/AnyTone-Software/Firmware-Update-Tool.zip" },
    @{ name = "Change-Log-D890UV-FW-v1.05.pdf";   url = "http://www.wouxun.us/Software/AnyTone-Software/Change-Log-D890UV-FW-v1.05.pdf" },
    @{ name = "AT-D890UV-Manual-and-Programming-Guides.zip"; url = "http://www.wouxun.us/Software/AnyTone-Software/AT-D890UV-Manual-&-Programming-Guides.zip" },
    @{ name = "Anytone-D890-Options.zip";         url = "http://www.wouxun.us/Software/AnyTone-Software/Anytone-D890-Options.zip" }
)
foreach ($item in $items) {
    $path = Join-Path $dest $item.name
    if (Test-Path $path) { Write-Host "exists  $($item.name)"; continue }
    Write-Host "getting $($item.name)"
    try {
        Invoke-WebRequest -Uri $item.url -OutFile $path -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -TimeoutSec 600
    } catch {
        Write-Host "FAILED  $($item.name): $($_.Exception.Message)"
    }
}
Get-ChildItem $dest -File | ForEach-Object {
    $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    "{0,-50} {1,12} {2}" -f $_.Name, $_.Length, $h
} | Tee-Object -FilePath (Join-Path $dest "SHA256SUMS.txt")
