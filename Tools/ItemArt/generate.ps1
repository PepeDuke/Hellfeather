# Generates the item reference images with the local ComfyUI pixel-art workflow and
# stores them as Assets/ItemArt/<Item>.png. Run convert.py afterwards to turn them
# into Source/ItemPictures.dk.
#   ./generate.ps1                      every item
#   ./generate.ps1 -Only Ring,Amulet    some items
#   ./generate.ps1 -Only Ring -Seed 11  another variation
param(
    [string[]]$Only,
    [int]$Seed = -1,
    [string]$Launcher = 'E:\AI\Run-PixelArt.ps1'
)
$ErrorActionPreference = 'Stop'
$config = Get-Content -Raw (Join-Path $PSScriptRoot 'items.json') | ConvertFrom-Json
$assets = Join-Path $PSScriptRoot '../../Assets/ItemArt'
New-Item -ItemType Directory -Force $assets | Out-Null
foreach ($property in $config.items.PSObject.Properties) {
    $name = $property.Name
    if ($Only -and $Only -notcontains $name) { continue }
    $itemSeed = if ($Seed -ge 0) { $Seed } elseif ($property.Value.seed) { $property.Value.seed } else { $config.seed }
    $prompt = "Pixel art of $($property.Value.prompt), $($config.style)"
    $lines = & $Launcher -Prompt $prompt -Seed $itemSeed
    $image = $lines | Where-Object { $_ -match '\.png$' } | Select-Object -Last 1
    if (-not $image) { throw "No image was saved for $name" }
    Copy-Item -LiteralPath $image -Destination (Join-Path $assets "$name.png") -Force
    "$name <- $image (seed $itemSeed)"
}
