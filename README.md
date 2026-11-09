# Hellfeather
 Hellfeather is a dark fantasy action RPG inspired by Diablo II, built with Quaxel Engine using the Duck programming language. Battle demonic creatures, explore cursed dungeons, collect legendary loot, and fight your way through a world consumed by darkness and feathers.


## Development

Game code lives in `Source/`. `Hellfeather.dkp` references the separate
`../Quaxel-Engine/Quaxel.Headless.dkp` library project. The Windows configuration
references `Quaxel.Windows.dkp`. Only this game defines `Main`.
Keep Duck, Quaxel-Engine and Hellfeather as sibling directories by default.

```powershell
# From this repository (builds the engine and game together):
./build.ps1
./.duck/build/debug/Hellfeather.exe

# Optimized build:
./build.ps1 -Profile release
./.duck/build/release/Hellfeather.exe
```

Use `-DuckRoot <path>` to locate another Duck toolchain. Build that toolchain
first with CMake as described in the Quaxel Engine README. Changing the engine
location requires updating `references` in both game manifests.

The default headless executable runs three simulation steps totaling 0.05 seconds.
Build outputs are ignored under `.duck/`.

Gameplay tests run without a GPU:

```powershell
../Duck/duck.cmd test Hellfeather.dkp
```

## Selecting a backend

```powershell
./build.ps1 -Platform headless
./.duck/build/debug/Hellfeather.exe

./build.ps1 -Platform windows
./.duck/build/windows/debug/Hellfeather.exe
```

Both configurations compile the same game source. The x64 Windows build
requires the Vulkan SDK. It opens a resizable window showing a voxel warrior in a generated world of valleys, rivers and mountains
from an isometric camera following the player. Clearing types live in `Source/Terrain.dk`. WASD moves the warrior and turns her to face her direction of travel. Evil ducks wait in the clearings in groups, chase her once she comes near and peck when in reach. Enemy types and groups are data in `Source/EnemyData.dk`, and `Source/EnemySpawner.dk` rolls them into the level and wakes them as she approaches. I opens the inventory on the right, where clicking picks up, places and equips items. Clicking elsewhere swings her axe, three hits slay a duck for good, and ten pecks down her until she returns three seconds later. Only hand-placed enemies marked `Respawns=true`, like the duck beside the church, come back after being slain. Enemies have a chance to drop items and gold, set by the loot tables in `Source/EnemyData.dk`. Each item is drawn once in `Source/ItemArt.dk`, which gives it both its inventory icon and its voxel model. Clicking the world while holding an item drops it beside her, and clicking a nearby item or its title picks it up. Health and mana show as voxel globes in the bottom corners, built in `Source/Globes.dk`. Rendering
pauses while the window is minimized. Models live in `Assets/`. The HUD in `Source/Hud.dk` is written in
Duck markup. Close the window to exit.
