param(
    [ValidateSet('debug', 'release')]
    [string]$Profile = 'debug',
    [ValidateSet('headless', 'windows')]
    [string]$Platform = 'headless',
    [string]$DuckRoot = (Join-Path $PSScriptRoot '../Duck')
)
$ErrorActionPreference = 'Stop'
$builder = Join-Path $DuckRoot 'duck.cmd'
if (-not (Test-Path -LiteralPath $builder)) {
    throw "Duck build launcher not found: $builder. Supply -DuckRoot."
}
$manifest = if ($Platform -eq 'windows') { 'Hellfeather.Windows.dkp' } else { 'Hellfeather.dkp' }
& $builder build (Join-Path $PSScriptRoot $manifest) --profile $Profile
exit $LASTEXITCODE
