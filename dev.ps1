# Start the backend (uvicorn :8000) and frontend (vite :5173) together.
# Ctrl+C stops both.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path backend/.env)) {
    Write-Error "backend/.env not found - copy backend/.env.example to backend/.env and add your OPENAI_API_KEY"
    exit 1
}
if (-not (Select-String -Path backend/.env -Pattern '^OPENAI_API_KEY=sk-' -Quiet)) {
    Write-Warning "OPENAI_API_KEY does not look set in backend/.env - ingest and chat will fail"
}

$backend  = Start-Process -PassThru -NoNewWindow -WorkingDirectory "$PSScriptRoot/backend" `
    python -ArgumentList "-m", "uvicorn", "main:app", "--port", "8000"
$frontend = Start-Process -PassThru -NoNewWindow -WorkingDirectory "$PSScriptRoot/frontend" `
    npm -ArgumentList "run", "dev"

Write-Host "backend  -> http://localhost:8000  (API docs: http://localhost:8000/docs)"
Write-Host "frontend -> http://localhost:5173"
Write-Host "Ctrl+C stops both."

try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    Stop-Process -Id $backend.Id, $frontend.Id -ErrorAction SilentlyContinue
}
