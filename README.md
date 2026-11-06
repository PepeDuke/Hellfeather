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

The current executable is a headless integration bootstrap: three simulation
steps totaling 0.05 seconds. It does not yet contain an RPG, window or renderer.
Engine code remains in Quaxel-Engine; game rules and content belong here.
Build outputs are ignored under `.duck/`.


## Selecting a backend

```powershell
./build.ps1 -Platform headless
./.duck/build/debug/Hellfeather.exe

./build.ps1 -Platform windows
./.duck/build/windows/debug/Hellfeather.exe
```

Both configurations compile the same game source. Gameplay imports Quaxel's
shared `quaxel_platform` API, never Windows/backend modules directly. The Windows
backend currently provides a clock, not window creation; the sample still runs
three headless simulation steps in either configuration. A future Linux backend
will use this same API. See Quaxel's `Docs/Platform.md` for the contract.
