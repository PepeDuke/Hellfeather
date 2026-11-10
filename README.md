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
from an isometric camera following the player. Clearing types live in `Source/Terrain.dk`. She starts inside the walls of Ravenford, laid out in `Source/Ravenford.dk` and drawn in `Source/RavenfordArt.dk`. Its gate opens onto the single road that joins the town to the rest of the level. WASD moves the warrior and turns her to face her direction of travel. Evil ducks wait in the clearings in groups, chase her once she comes near and peck when in reach. Enemy types and groups are data in `Source/EnemyData.dk`, and `Source/EnemySpawner.dk` rolls them into the level and wakes them as she approaches. I opens the inventory on the right, where clicking picks up, places and equips items. Clicking elsewhere swings her axe, three hits slay a duck for good, and ten pecks down her until she returns three seconds later. Only hand-placed enemies marked `Respawns=true`, like the duck on the road past the bridge, come back after being slain. Enemies have a chance to drop items and gold, set by the loot tables in `Source/EnemyData.dk`. Each item is drawn once, which gives it both its inventory icon and its voxel model. The pictures in `Source/ItemPictures.dk` are generated: `Tools/ItemArt/generate.ps1` makes a pixel-art image per item with the local ComfyUI workflow into `Assets/ItemArt`, and `python Tools/ItemArt/convert.py` scales each one to its inventory size and the palette in `Source/ItemArt.dk` (needs Pillow). Prompts and per-item options live in `Tools/ItemArt/items.json`. Icons carry only colors; the UI shader draws their one-pixel outline. Clicking the world while holding an item drops it beside her, and clicking a nearby item or its title picks it up. Health and mana show as voxel globes in the bottom corners, built in `Source/Globes.dk`. Between them sits the action bar, whose five slots answer the left and right mouse buttons and the Q, E and F keys. Clicking a slot opens a picker above the bar, and clicking an action there puts it in the slot. The axe swing and the two potions are known from the start, and potions drink from the bag. The agilities Cleave, War Cry and Dash cost mana, which slowly returns, and are learned after slaying 3, 8 and 15 enemies, landing in the first empty slot. Actions and their costs live in `Source/Actions.dk`, the bar in `Source/ActionBar.dk` and its pixel art in `Source/ActionArt.dk`. Rendering
pauses while the window is minimized. Models live in `Assets/`. The HUD in `Source/Hud.dk` is written in
Duck markup. Close the window to exit.
