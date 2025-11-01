<#
.SYNOPSIS
  Clean common temporary files and virtual environments for the project (Windows PowerShell).

.DESCRIPTION
  Removes .venv, .venv_migration, __pycache__, .pytest_cache, and *.pyc files. Clears files inside the
  logs/ directory but keeps the directory itself.
#>

Write-Host "Cleaning project workspace..."

$pathsToRemove = @('.venv', '.venv_migration', 'venv', 'env', '__pycache__', '.pytest_cache')

foreach ($p in $pathsToRemove) {
    if (Test-Path $p) {
        Write-Host "Removing: $p"
        Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Remove .pyc files
Get-ChildItem -Path . -Recurse -Include *.pyc -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
}

# Clear logs but keep directory
if (Test-Path logs) {
    Get-ChildItem -Path logs -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Clean complete."