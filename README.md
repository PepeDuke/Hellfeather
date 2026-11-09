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
requires the Vulkan SDK. It opens a resizable window showing an 8×8×8 voxel player cube on an 80×1×80 voxel ground plane
from an isometric camera attached to the cube. WASD moves the cube. Rendering
pauses while the window is minimized. Close the window to exit.
