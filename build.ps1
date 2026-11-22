param(
    [ValidateSet('debug', 'release')]
    [string]$Profile = 'debug',
    [ValidateSet('headless', 'windows', 'web')]
    [string]$Platform = 'headless',
    [string]$DuckRoot = (Join-Path $PSScriptRoot '../Duck')
)
$ErrorActionPreference = 'Stop'
$builder = Join-Path $DuckRoot 'duck.cmd'
if (-not (Test-Path -LiteralPath $builder)) {
    throw "Duck build launcher not found: $builder. Supply -DuckRoot."
}
$manifest = if ($Platform -eq 'web') { 'Hellfeather.Web.dkp' } elseif ($Platform -eq 'windows') { 'Hellfeather.Windows.dkp' } else { 'Hellfeather.dkp' }
if ($Platform -eq 'windows') { & (Join-Path $PSScriptRoot '../Quaxel-Engine/configure-vulkan.ps1') }
& python (Join-Path $PSScriptRoot '../Quaxel-Engine/Tools/Qvoxc/compile.py') (Join-Path $PSScriptRoot 'Assets') --duck-root $DuckRoot
if ($LASTEXITCODE) { exit $LASTEXITCODE }
if ($Platform -eq 'web') {
    & (Join-Path $PSScriptRoot '../Quaxel-Engine/Tools/Web/build.ps1') -Builder $builder -Manifest (Join-Path $PSScriptRoot $manifest) -Profile $Profile -AssetExtensions '.qvox','.qvoxc','.wav','.ico'
    exit $LASTEXITCODE
}
& $builder build (Join-Path $PSScriptRoot $manifest) --profile $Profile
exit $LASTEXITCODE
