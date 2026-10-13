param([string]$Python = '', [int]$Port = 8766)
if ($Port -ne 8766) { throw 'Stage 01 uses port 8766. Change configured origins deliberately before using another port.' }
. (Join-Path $PSScriptRoot 'scripts/foundation-env.ps1') -Python $Python
Push-Location $FoundationBackend
try {
    & $FoundationPython -m app.server
} finally { Pop-Location }
