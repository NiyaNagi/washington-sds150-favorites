param()
$dev = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like '*VID_067B*' } | Select-Object -First 1
if (-not $dev) { 'No Prolific device present.'; exit 1 }
"InstanceId : $($dev.InstanceId)"
"Status     : $($dev.Status)"
"Name       : $($dev.FriendlyName)"
Get-PnpDeviceProperty -InstanceId $dev.InstanceId |
    Where-Object { $_.KeyName -match 'ProblemCode|DriverVersion|DriverDate|DriverProvider|DriverInfPath' } |
    ForEach-Object { '{0,-30} {1}' -f $_.KeyName, ($_.Data -join ', ') }
''
'--- serial ports ---'
Get-CimInstance Win32_SerialPort | Select-Object DeviceID, Description, PNPDeviceID | Format-Table -AutoSize | Out-String -Width 160
''
'--- prolific drivers in the driver store ---'
$out = pnputil /enum-drivers
$block = @()
foreach ($line in $out) {
    if ($line -match '^\s*$') {
        if (($block -join ' ') -match 'ser2pl|prolific') { $block | ForEach-Object { "  $_" }; '' }
        $block = @()
    } else { $block += $line }
}
