param()
$dev = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like '*VID_067B*' } | Select-Object -First 1
if (-not $dev) { 'No Prolific device present.'; exit 1 }
'Name    : ' + $dev.FriendlyName
'Status  : ' + $dev.Status
Get-PnpDeviceProperty -InstanceId $dev.InstanceId |
    Where-Object { $_.KeyName -match 'ProblemCode|DriverVersion|DriverInfPath|DriverDate' } |
    ForEach-Object { '{0,-30} {1}' -f $_.KeyName, ($_.Data -join ', ') }
$k = 'HKLM:\SYSTEM\CurrentControlSet\Enum\' + $dev.InstanceId + '\Device Parameters'
if (Test-Path $k) { 'PortName: ' + (Get-ItemProperty $k).PortName }
'Ports   : ' + ([System.IO.Ports.SerialPort]::GetPortNames() -join ', ')
