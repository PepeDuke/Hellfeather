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
from an isometric camera following the player. Clearing types live in `Source/Terrain.dk`. She starts inside the walls of Ravenford, laid out in `Source/Ravenford.dk` and drawn in `Source/RavenfordArt.dk`. Its gate opens onto the single road that joins the town to the rest of the level. WASD moves the warrior and turns her to face her direction of travel. Evil ducks wait in the clearings in groups, chase her once she comes near and peck when in reach. Enemy types and groups are data in `Source/EnemyData.dk`, and `Source/EnemySpawner.dk` rolls them into the level and wakes them as she approaches. I opens the inventory on the right, where clicking picks up, places and equips items. Clicking elsewhere swings her hand axe, four hits slay a duck for good, and ten pecks down her until she returns three seconds later. Only hand-placed enemies marked `Respawns=true`, like the duck on the road past the bridge, come back after being slain. Enemies have a chance to drop items and gold, set by the loot tables in `Source/EnemyData.dk`. Each zone has an area level (`HellfeatherZoneNames.Level` in `Source/Zones.dk`) that rises from Ravenford out to the Undercroft, and each loot entry's `MinLevel` and `MaxLevel` gate the item bases it drops, so later zones roll better bases such as ring mail, great helms and flanged maces. Each item is drawn once, which gives it both its inventory icon and its voxel model. The pictures in `Source/ItemPictures.dk` are generated: `Tools/ItemArt/generate.ps1` makes a pixel-art image per item with the local ComfyUI workflow into `Assets/ItemArt`, and `python Tools/ItemArt/convert.py` scales each one to its inventory size and the palette in `Source/ItemArt.dk` (needs Pillow). Prompts and per-item options live in `Tools/ItemArt/items.json`. Icons carry only colors; the UI shader draws their one-pixel outline. An item without an image of its own borrows the picture of the plain item it looks most like (`Likeness` in `Source/ItemArt.dk`). Helmets lie on the ground as the model she wears on her head, and weapons, shields and helmets show on her through the models `Tools/Models/gear.py` writes to `Assets/`. Clicking the world while holding an item drops it beside her, and left-clicking a nearby item or its title picks it up. A right click, or a left click on an item out of her reach, still uses its action. Pointing at an enemy names it on a plate at the top of the screen, whose border runs around the plate as its health bar; the name takes the enemy's rank color (normal, magic, rare or unique), set by `Rank` in `Source/EnemyData.dk` and drawn by `Source/EnemyPlate.dk`. Tab lays the automap over the middle of the view: the ground she has seen in each level, outlined against rock and buildings and turned like the camera's view, with her, the townsfolk, doors, stairs and open portals marked on it (`Source/AutoMap.dk`). Health and mana show as voxel globes in the bottom corners, built in `Source/Globes.dk`. Between them sits a raven-framed action bar. Its two largest wells are left and right click. The four numbered slots sit over Q, E and F, with a dedicated H button for raven portals at the right. The five icons stacked at the left end of the action bar open Runes (R), Inventory (I), Quests (L), Stats (C) and Passives (P). Clicking a slot opens a picker above the bar, and clicking an action there puts it in the slot. The axe swing and the two potions are known from the start, and potions drink from the bag. The agilities Cleave, War Cry and Dash cost mana, which slowly returns, and are known while their rune sits on the rune board (R), landing in the first empty slot. She starts with the Cleave rune socketed, so Cleave sits on the right mouse button from the start. Actions and their costs live in `Source/Actions.dk`, the bar in `Source/ActionBar.dk` and its pixel art in `Source/ActionArt.dk`. Cleave sweeps the axe level across the front of her, hitting what stands before and beside her and leaving an arc of light; War Cry has her throw her arms wide and yell, and a shockwave rolls out from her. Swings and the cry played on the move keep her legs walking. Weapons deal a range of damage, rolled anew for every blow. Defense and enemy armor work as dodging: the lead of armor over the attacker's accuracy buys a chance to dodge that grows ever more slowly and never reaches 38%, so every blow can land. Later enemies add fire, cold or lightning to their physical damage, which her resistances lower. The rules live in `Source/Combat.dk`, and the stats panel (C) shows her damage range, accuracy and defense with its dodge chance. Rendering
pauses while the window is minimized. Models live in `Assets/`. The HUD in `Source/Hud.dk` is written in
Duck markup. Close the window to exit.

## Ravenford walking benchmark

From the repository root, build and run the Windows release executable.

```powershell
./build.ps1 -Platform windows -Profile release
./.duck/build/windows/release/Hellfeather.exe --benchmark
```

The benchmark opens a 1920x1080 window and warms up at the normal Ravenford spawn for 30 simulation ticks, holds A
for 120 ticks (two simulated seconds), then closes the window. The console reports
window resolution, frame count, mean frame time, average FPS, and horizontal distance from spawn.
The benchmark requests immediate presentation, falling back to mailbox and then FIFO, and prints the selected mode.
Wall time includes presentation pacing. The summary also reports main-thread CPU
execution (Windows user + kernel thread time) and GPU elapsed time between Vulkan
timestamps bracketing the frame command buffer, including the final image copy.
CPU and GPU can overlap. Windows thread accounting can give coarse individual
samples, so use the CPU average over the walk for comparisons. Leave the window
at its initial size and keep it active when comparing builds.

Add `--frame-times` to record each measured frame. After the walk, the game prints
the total elapsed milliseconds and three series in matching frame order: wall,
main-thread CPU, and GPU milliseconds.
To save the summary and samples together, run:

```powershell
./.duck/build/windows/release/Hellfeather.exe --benchmark --frame-times > ravenford-frame-times.txt
```

The benchmark reports mean GPU lighting-pass time. Use `--benchmark-lights 0`,
`--benchmark-lights 1`, or `--benchmark-lights 12` for the same walk with a
fixed set of shadow-casting test lights around spawn. Add `--unshadowed-test-lights`
to compare the same test lights with their shadows disabled. Fire and smoke effects run in every
case. Plain `--benchmark` uses the regular brazier and campfire lights. DDGI is enabled by default.
Add `--no-ddgi` for the original ambient lighting or `--ddgi-uniform` to distribute the same 4,096 rays uniformly across resident probes. The lighting GPU timer includes
probe tracing, probe blending and the fullscreen lighting pass.
