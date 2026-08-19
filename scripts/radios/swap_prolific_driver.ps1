param()
$log = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\.drivers\swap.log'))
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
'' | Set-Content $log

function Write-Log { param($m) $m | Tee-Object -FilePath $log -Append | Write-Host }

Write-Log "=== Prolific driver swap  $(Get-Date -Format 'HH:mm:ss') ==="
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Log "elevated: $admin"
if (-not $admin) { Write-Log 'NOT ELEVATED - nothing can be changed.'; Start-Sleep 25; exit 1 }
Write-Log ''

$dev = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like '*VID_067B*' } | Select-Object -First 1
if (-not $dev) { Write-Log 'No Prolific device present. Plug the cable in and re-run.'; Start-Sleep 25; exit 1 }
Write-Log "device: $($dev.InstanceId)"
Write-Log ''

Write-Log '--- removing the blocking package oem168.inf (3.8.43.0) ---'
(& pnputil /delete-driver oem168.inf /uninstall /force 2>&1) | ForEach-Object { Write-Log "  $_" }
Write-Log "exit code: $LASTEXITCODE"
Write-Log ''

Write-Log '--- rescanning ---'
(& pnputil /scan-devices 2>&1) | ForEach-Object { Write-Log "  $_" }
Start-Sleep -Seconds 5
Write-Log ''

Write-Log '--- result ---'
$dev = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like '*VID_067B*' } | Select-Object -First 1
if ($dev) {
    Write-Log "Name    : $($dev.FriendlyName)"
    Write-Log "Status  : $($dev.Status)"
    Get-PnpDeviceProperty -InstanceId $dev.InstanceId |
        Where-Object { $_.KeyName -match 'ProblemCode|DriverVersion|DriverInfPath' } |
        ForEach-Object { Write-Log ('{0,-30} {1}' -f $_.KeyName, ($_.Data -join ', ')) }
} else {
    Write-Log 'Device is gone; unplug and replug the cable.'
}
Write-Log ('Ports   : ' + ([System.IO.Ports.SerialPort]::GetPortNames() -join ', '))
Write-Log ''
Write-Host 'Finished. Window closes in 30 seconds.' -ForegroundColor Green
Start-Sleep -Seconds 30
