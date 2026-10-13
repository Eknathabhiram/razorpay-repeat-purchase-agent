param([string]$Python = '', [switch]$InstallDependencies)
. (Join-Path $PSScriptRoot 'foundation-env.ps1') -Python $Python
Push-Location $FoundationBackend
try {
    if ($InstallDependencies) {
        # The lock includes all application dependencies. Only Twilio's standalone
        # RequestValidator is used; HTTP transport uses the existing httpx client.
        & $FoundationPython -m pip install --no-deps --target .local/foundation -r requirements-foundation.lock
        if ($LASTEXITCODE) { throw 'Dependency installation failed.' }
    }
    & $FoundationPython scripts/prepare_postgres.py --download --start
    if ($LASTEXITCODE) { throw 'Project PostgreSQL setup failed.' }
    & $FoundationPython -m alembic upgrade head
    if ($LASTEXITCODE) { throw 'Migration failed.' }
    & $FoundationPython -m app.cli bootstrap
    if ($LASTEXITCODE) { throw 'Owner bootstrap failed.' }
} finally { Pop-Location }
