$original = "d:\Dichtrung\Output\Linh Hon Negary_Hu Minh\Story-TimeLine.jsonl"
$scratch = "d:\Dichtrung\scratch\new_timeline_lines.txt"
$content = Get-Content $original -Encoding UTF8
$truncated = $content[0..106]
$newLines = Get-Content $scratch -Encoding UTF8
$final = $truncated + $newLines
$final | Out-File $original -Encoding UTF8
