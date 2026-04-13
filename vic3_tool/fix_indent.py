$content = Get-Content 'ui/tabs/event_tab.py' -Raw
$lines = $content -split "`n"
$lines[65..80] | ForEach-Object { $i = [array]::IndexOf($lines, $_) + 1; "Ligne {0,3} |{1}|" -f $i, $_.Replace(' ', '·') }

