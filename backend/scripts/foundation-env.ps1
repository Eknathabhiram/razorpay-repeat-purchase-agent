param([string]$Python = '')
$foundationBackend = Split-Path $PSScriptRoot -Parent
if (-not $Python) {
    $foundationBundled = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $foundationBundled) { $Python = $foundationBundled } else { $Python = 'python' }
}
$env:PYTHONPATH = ((Join-Path $foundationBackend '.local/foundation'), $foundationBackend) -join ';'
$script:FoundationPython = $Python
$script:FoundationBackend = $foundationBackend
