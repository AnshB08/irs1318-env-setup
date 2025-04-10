function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

Write-Host "`nInstalling uv..." -ForegroundColor Cyan
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}
else {
    Write-Host "uv is already installed"
}

Refresh-Path

uv python install 3.12.8

$scriptUrl = "https://raw.githubusercontent.com/AnshB08/irs1318-env-setup/refs/heads/main/install.py"
$tempFile = "$env:TEMP\install.py"

Invoke-WebRequest -Uri $scriptUrl -OutFile $tempFile

uv run $tempFile

Refresh-Path
