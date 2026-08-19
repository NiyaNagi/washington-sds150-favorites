param()
$out = pnputil /enum-drivers
$block = @()
foreach ($line in $out) {
    if ($line -match '^\s*$') {
        $joined = $block -join ' '
        if ($joined -match 'ser2pl|Prolific') {
            $block | Where-Object { $_ -match 'Published Name|Original Name|Provider Name|Driver Version|Class Name' } |
                ForEach-Object { "  $($_.Trim())" }
            ''
        }
        $block = @()
    } else { $block += $line }
}
