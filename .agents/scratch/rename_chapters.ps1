$dir = "d:\Dichtrung\Output\Ta Trong Binh Vu Tru_Tam Bach Can Dich Vi Tieu\output\"
$files = Get-ChildItem "$dir\00[5-9][0-9] - *.md", "$dir\0100 - *.md"
foreach ($file in $files) {
    $content = Get-Content $file.FullName -Encoding UTF8 -Raw
    # Very flexible regex: capture first number after # and anything after a dash or colon
    if ($content -match "(?m)^#\s*\w*\s*(\d+)\s*[-:]\s*(.*)") {
        $num = $matches[1].PadLeft(4, '0')
        $title = $matches[2].Trim()
        $title = $title -replace '[\\/:*?"<>|]', ''
        $newName = "Chương $num - $title.md"
        $newPath = Join-Path $dir $newName
        Write-Host "Renaming $($file.Name) to $newName"
        if (-not (Test-Path $newPath)) {
            Move-Item $file.FullName $newPath -Force
        } else {
            Write-Host "File already exists: $newName"
            # If the current file is the legacy one, we should remove it
            if ($file.Name -notmatch "^Chương") {
                Remove-Item $file.FullName -Force
            }
        }
    } else {
        Write-Host "Pattern not found in $($file.Name)"
    }
}
