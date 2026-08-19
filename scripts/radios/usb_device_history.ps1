param()
foreach ($vid in 'VID_3679', 'VID_067B') {
    "=== $vid ==="
    $devs = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "*$vid*" }
    foreach ($d in $devs) {
        "  $($d.FriendlyName)"
        "    InstanceId: $($d.InstanceId)"
        foreach ($key in 'DEVPKEY_Device_InstallDate', 'DEVPKEY_Device_FirstInstallDate', 'DEVPKEY_Device_LastArrivalDate', 'DEVPKEY_Device_Manufacturer', 'DEVPKEY_Device_BusReportedDeviceDesc') {
            try {
                $p = Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName $key -ErrorAction Stop
                if ($p.Data) { '    {0,-34} {1}' -f $key.Replace('DEVPKEY_Device_', ''), $p.Data }
            } catch { }
        }
    }
    ''
}
