param([string]$Python = '')
. (Join-Path $PSScriptRoot 'foundation-env.ps1') -Python $Python
Push-Location $FoundationBackend
try {
    & $FoundationPython -m unittest discover -s tests -v
    if ($LASTEXITCODE) { throw 'PostgreSQL foundation tests failed.' }
    & $FoundationPython -m unittest test_shopify_app -v
    if ($LASTEXITCODE) { throw 'Existing Shopify compatibility tests failed.' }
} finally { Pop-Location }
