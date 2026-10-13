param([string]$Python = 'python')
$env:PYTHONPATH = Join-Path $PSScriptRoot '.local/python'
Push-Location $PSScriptRoot
try {
    & $Python -m uvicorn shopify_app:app --host 127.0.0.1 --port 8765 --no-access-log
} finally {
    Pop-Location
}
