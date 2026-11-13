# Act I — Models to make

## Status (built from the concept sheets)

Every model below except Wren's rework now exists in `Assets/`, built by `Tools/Models/act1.py` from the sheets in `Act1-refs`. The tool crops each sheet's front and side views into `Assets/Reference/Act1`, makes the model solid where both silhouettes agree, and poses enemies and people into clips by bending that hull (pitching the upper body, swinging the legs). The raven's frames come straight from its sprite atlas, and the Silver Spark is generated.

```
python Tools/Models/act1.py --import <folder of sheets>   crop the views (once)
python Tools/Models/act1.py --preview                      build every model, with renders in Tools/Models/Preview
python Tools/Models/act1.py RoadDrake Moth                 rebuild some of them
```

- **Buildings are moving to recipes.** Two outlines can't make a round tower round, and the sheet's painted light gets baked into the voxels, so buildings built by `act1.py` come out boxy and muddy. `Tools/Models/buildings.py` builds them instead from `kit.py` parts (tapered round shafts, octagonal roofs, plank walls, beams, ravens), using proportions measured off the sheet and a small fixed palette of materials (stone courses, planks, shingles, droppings, moss, lamp glow). Done: all eight buildings (`RookeryTower`, `CrookedRaven`, `ReevesHall`, `PellsChandlery`, `SennsNeedlehouse`, `LanternAndMoth`, `OrrasHospice`, `HobbsMill`). House parts (timber-framed and stone walls, gable roofs with sag, lattice/barred/candle/cloth windows, doors, chimneys, outside stairs, signs, barrels, sacks, the water wheel) live in `house.py`. Each building stays inside the half and height its placement in `Ravenford.dk` or `Fenmarch.dk` gives it. Each recipe keeps its `act1.MODELS` entry, marked `recipe=True`, so `inspect_models.py` still scores it against the sheet and `act1.py` skips it.
  ```
  python Tools/Models/buildings.py RookeryTower --preview
  python Tools/Models/inspect_models.py RookeryTower
  ```
- **People are moving to rigs.** `Tools/Models/figure.py` is a small rig: bones with body and clothing parts (stacked-ellipse torsos and skirts, capsule limbs, apron layers, hair caps, held things) painted from `kit.py` materials. Poses turn the bones, so `idle` and `talk` are real motion. Recipes are in `Tools/Models/people.py` (a shared `Body` builder does boots, legs, skirts and coat tails, torso, aprons, belts, arms, head, face and four hair styles), marked `recipe=True` in `act1.MODELS`. Done: `Edda`, `Matthew`, `ReeveHollan`, `MarraSenn`, `Moth`, `SisterCarmine`, `SisterVale`, `OldHobb`, `LiseHobb` and the static `JessaBed`. Everyone is authored 70 rig voxels tall and scaled to Cast.dk's height. Each model's file lists only the colours it uses, since the kit now has more colours than qvox's 92 one-character symbols. Each person must stay as tall as the height `Cast.dk` gives `AddPerson`.
  ```
  python Tools/Models/people.py Edda --preview
  ```
- **Enemies are moving to rigs too.** `Tools/Models/enemies.py` builds them on the same rig, with walking legs and the five clips the game plays. The attack's wind-up frames add up to 270 ms, because `EnemyMoves.WindUp` stretches them to the move's wind-up, and the blow lands on the kind's `StrikeFrame` in `EnemyData.dk`. Done: `PilgrimPenitent` (StrikeFrame 4: four wind-up frames, then the slam, follow-through and recovery). Done since: every other Act I enemy. People-shaped ones share `Body`, `legs` and `human_clips`; ducks, geese and corvids share `Bird` and `bird_clips` (peck, hop, charge, wing slam, spit, dive); the leech is a tail-to-head chain of segments. Their attacks land on frame 2, the default. `Height` in `EnemyData.dk` (and the height `Cast.dk` gives a person) must be the model's box height, the middle number the build prints, because the game stands a model by half that height: a box taller than `Height` sinks into the ground. The Evil Duck is rebuilt too, as the Story's mallard (`EvilDuck` in `enemies.py`), so every enemy now lands its blow on frame 2. Only the five clips the game plays are built: the sheets' extra clips (swim, flee, freed, emerge, ringpull, broodcall, moult, stagger) wait until the game can play them. Every frame is stored whole, so models whose clips reach far (wing slams, charges, death rolls) are big files: up to about 17 MB.
  ```
  python Tools/Models/enemies.py PilgrimPenitent --preview
  ```
- **Wren and her gear.** `Tools/Models/player.py` builds Wren on the rig twice, from the same bones, clips and sockets: `Warrior.qvox` in her basic attire (vest and shorts, barefoot, the Tithe-mark) and `WarriorLeatherArmor.qvox` in Leather Armor (the oilcloth coat, jerkin, boots and scarf). Both share one box, so `HellfeatherWarrior.Height` (81) fits either. Every frame carries three sockets: `hand_r` for the weapon (hanging head-down with the Battle Axe's big blade turned back, so the wind-up lifts it overhead and the strike brings the big blade down; check a turn with `inspect_models.py <body> --gear hand_r=BattleAxe`, which places gear exactly as the engine does, and try others with `--twist`), `hand_l` for the shield and `head` for the helmet. `Tools/Models/gear.py` builds what rides them, at her scale, each with a `grip`: `MinersHelmet`, `IronHelm`, `RoundShield`, `ShortSword` and `MillstoneMaul`; `BattleAxe.qvox` is the hand-made original. In game, `HellfeatherWardrobe` (`Warrior.dk`) swaps her body for the Body slot and puts the Head, MainHand and OffHand items on their sockets whenever they change. She starts in plain Leather Armor and the Miner's Helmet with her axe. A new body armor needs a variant in `player.py` and a line in `HellfeatherWarrior.BodyModel`; a new helmet, weapon or shield needs a recipe in `gear.py` and a line in `HellfeatherWarrior.GearModel`.
  ```
  python Tools/Models/player.py --preview
  python Tools/Models/gear.py
  ```
- **The raven** is rebuilt by `Tools/Models/raven.py` on the Bird rig, with two sets of wings: folded while it sits, and jointed spread wings (arm, hand and fingered primaries) for `fly` and `land`. The clips keep the sprite atlas's names and timings. Its voxels are 0.025 like the people's, and `HellfeatherRavens.Height` is its box height (37). Perched it sits as a raven does: chest up, a short neck, the bill level and the long tail sloping toward the perch. `act1.py` no longer builds it.
  ```
  python Tools/Models/raven.py --preview
  ```
- All of them are wired into the game: enemies in `EnemyData.dk`, people in `Cast.dk`, buildings in `Ravenford.dk` and `Fenmarch.dk`, Undercroft props in `Undercroft.dk`, everything else in `Landmarks.dk`.
- Palettes are converted from the sheets' sRGB to linear light, because the engine reads qvox colors as linear.
- Animated models taller than 72 voxels use coarser voxels so their files stay small. The tool prints each one's voxel size, and `EnemyData.dk` and `Cast.dk` use those sizes.
- **Not built yet:** the Wire Floor and Black Feathers flat props, and new item pictures. Act I's items borrow the picture of the plain item they look most like (`HellfeatherItemArt.Likeness`).
- The hull-and-bend poses are serviceable rather than hand-animated. Hand-made clips in the same files can replace them without code changes, as long as the clip names stay and attack clips land on their strike frame (frame 2 for generated models).

Everything Act I in [Story.md](Story.md) needs that the game doesn't have a model for yet. The game already runs without these models: each enemy borrows the Evil Duck model at its own scale until its file appears in `Assets/`, and the hospice and mill borrow the church and the ruined cottage. For **enemies**, dropping a file in with the name given is enough: the game picks it up with no code change. NPCs, buildings and props still need a line of code each to load and place them. Footprints are approximate and given in world units.

## Conventions

- **Characters and creatures** are `.qvox` files with voxels 0.025 world units wide. Heights are in voxels; Wren is 78 (1.95 units) and the Evil Duck is 66. They face local +Z.
- **Reference sheets** for the `Tools/Models/shopkeeper.py` pipeline: a front view and a side view of the same figure, full body, feet on the bottom edge, plain near-black background, flat light, no cast shadow. Muted dark-fantasy palette. Rain-wet, grey and brown, with black feathers as the accent.
- **Enemy clips**, named as in `EvilDuck.qvox`: `idle` and `walk` loop, while `attack`, `hit` and `death` play once. "Attack" below describes what the clip should show.
- **NPCs** stand still facing the camera, like the Shopkeeper. One pose, with an optional `idle` loop.
- **Buildings and props** use 0.0625-unit voxels, as Ravenford's do. The door and the side that matters face +Z, toward the camera. Footprints are in world units.
- Each Act I enemy has one move with a clear wind-up (elites have two), so every `attack` clip needs a readable anticipation pose before the hit.

---

## 1. Player

| File | Height | Description |
|---|---|---|
| `Warrior.qvox` (rework, optional) | 78 | **Wren Carrow**, thief-taker and ex-miner. A lean woman in her thirties, worn oilcloth coat over a leather jerkin, miner's leather cap pushed back, scarf over her mouth for the Grey Cough. A rolled-up right sleeve shows the **Tithe-mark**: silver lines like a woven lattice running wrist to elbow. Woodsman's axe. Clips: `idle` (slight hunch, a cough every few loops), `walk`, `attack`. A `dash` clip (Lattice Step, a smeared lunge) would help later. |

## 2. NPCs (Ravenford, Orra's Hill, Hobb's Mill)

All are 70–74 voxels tall unless noted.

| File | Who | Look |
|---|---|---|
| `Matthew.qvox` | **Matthew the Journeyman**, Crooked Raven | Polite, neat, unremarkable. Travelling craftsman's brown coat, a tool roll on his back with no tools in it, a soft felt cap held in both hands. Too clean for the fen. The model should have no shadow-casting cloak edges. (In game his shadow falls toward the lamp.) |
| `Edda.qvox` | **Edda the Ravenkeeper**, Rookery Tower | Old, broad, blunt. Heavy leather apron streaked white with droppings, thick falconer's glove on the left arm with a raven perched on it, a sack of black feathers at her hip. Grey hair cropped short. |
| `ReeveHollan.qvox` | **Reeve Hollan**, Reeve's Hall | Middle-aged, tired, soft around the middle. Dark blue doublet with a brass chain of office, ink-stained fingers, a bundle of papers under one arm. |
| `MarraSenn.qvox` | **Marra Senn**, Senn's Needlehouse | Lean, sharp-faced woman of fifty. Pinned sleeves, a pincushion strapped to her wrist, measuring tape around her neck, a bandaged left thumb. Arms crossed. |
| `Moth.qvox` | **Moth**, the Lantern & Moth | Thin fence in a moth-grey velvet coat gone shiny at the elbows, a jeweller's loupe on a chain, rings on every finger. Holds a small shuttered lantern. |
| `SisterCarmine.qvox` | **Sister Carmine**, hospice gate | Hospice nurse in a grey habit with a starched red wimple and red apron, very red lips, a steel pen in her right hand. Upright and smiling. (She is Act II's boss, so a later rework will need clips.) |
| `Jessa.qvox` (lying, about 30 tall) | **Jessa Brune**, dying in the hospice | An emaciated weaver lying on a straw pallet with a grey blanket, black-stained lips, her right arm reaching out from the bed. One static pose. Make the bed part of the model. |
| `Vale.qvox` | **Sister Vale, the Grey Sister** | A tall woman in a long grey coat like a nun's habit cut for travel, hood down, hair the same grey as the coat, calm face. Hands folded. Her look should read as slightly wrong: one sleeve hangs as if a second arm were inside it. (The game adds the shadow that leans the wrong way.) |
| `OldHobb.qvox` | **Old Hobb**, Hobb's Mill | Stooped miller, flour in every crease, patched smock, cap twisted in his hands, eyes down. |
| `Lise.qvox` | **Lise Hobb**, on the mill stair | A young woman with a crutch under her left arm and a hip that sits wrong. Plain mill dress, flour-dusted apron, dark hair pinned up. Still, watching. |
| `SergeantOttar.qvox` | **Sergeant Ottar**, the Red Cuff ambush (unique enemy, I-3) | A Cuffman (see below) with a sergeant's red sash, a bladelock on his back and a greying beard. Enemy clips. |

## 3. Enemies

### Ford Road

| File | Height | Look | Attack clip |
|---|---|---|---|
| `EvilDuck.qvox` | 66 | *(exists)* | Peck |
| `RoadDrake.qvox` | 92 | A duck the size of a sheepdog, with bald grey moult patches and a thick neck bristling with black quills. | Puffs up for a full second, then charges with its head low. |
| `CarrionRook.qvox` | 40 | A small scruffy crow with one white-filmed eye. | Hops in, pecks once, hops back. |
| `TitheStray.qvox` | 72 | A thin bearer in wet sackcloth with grey lips, a tin tithe bracelet on one wrist and a shuffling gait. | A weak, slow slap. |

### Fennick Water

| File | Height | Look | Attack clip |
|---|---|---|---|
| `ReedDuck.qvox` | 62 | A duck slick with fen mud, reeds tangled on its back. Add a `swim` loop if you can: only the eyes and back above the waterline. | Peck |
| `Duckling.qvox` | 26 | Grey fluff with black pinfeathers pushing through, oversized feet. | A tiny peck. Swarms of 8–12, so keep the model cheap. |
| `MoultedGander.qvox` | 88 | A big grey goose, half bald, its long neck studded with black quills, beak open, hissing. | Rears its neck back, then a wing slam forward. |
| `BlackHoneyLeech.qvox` | 16 (about 36 long) | A fat glossy black leech the length of a forearm, with a sheen that runs *upward* like honey poured backwards. | A lunge-bite. `death` is a black splash. |
| `OldGreyneck.qvox` | 100 | **Unique.** An ancient gander, grey-white and scarred, one long quill standing up from its crown like a plume. | Honk (calls flocks) and a wing slam. |

### Orra's Hill

| File | Height | Look | Attack clip |
|---|---|---|---|
| `PilgrimPenitent.qvox` | 74 | Grey robes, bare feet, black feathers tied into hair and beard, carrying a tall shrine pole hung with feathers. | A slow overhead pole swing with a long wind-up. |
| `BlackHoneyFiend.qvox` | 70 | A gaunt addict with a black-stained mouth, eyes too bright, burned fingers and a kitchen knife. | Sprints, slashes twice, then stops doubled over for breath. That pause is the punish window, so make it visible. |
| `GallowsRook.qvox` | 44 | A corvid with a rope-burn ring of bare skin around its neck. Needs a perched `idle` and a wings-spread `walk` (flight). | A straight dive swoop. |

### Hobb's Mill & Millpond

| File | Height | Look | Attack clip |
|---|---|---|---|
| `PondDrake.qvox` | 70 | A duck whose throat glows faint silver, with silver droplets falling from its bill. | Rears back and spits a glowing water bolt. |
| `MillhandThrall.qvox` | 74 | A flour-caked mill worker, hollow-eyed, a ring-scar on one palm, carrying a full flour sack as a weapon. | A slow heavy sack swing. Add a `flee` loop (weapon dropped, running). |
| `Cuffman.qvox` | 76 | A Red Cuff soldier in a grey gambeson with red cloth at cuffs and collar, arming sword, kite shield. | A plain sword cut, with the shield held forward in `idle` and `walk`. |
| `BladelockArbalist.qvox` | 76 | A Red Cuff with a bladelock: a short blade nested under a crossbow stock, bolts etched with marks. | Aims for about a second, fires, then reloads slowly. |

### The Millrace Undercroft (dungeon, not built yet)

| File | Height | Look | Attack clip |
|---|---|---|---|
| `HollowedBearer.qvox` | 74 | A bearer chained into an iron frame, with silver wire bracelets on both wrists, milk-white eyes and skin like wet paper. The frame is part of the model. | Swipes from inside the frame. Add `freed`, where the chains fall and the bearer slumps out. |
| `BroodDrake.qvox` | 76 | An oversized, always-wet duck with silver veins showing through thin feathers. | A short leap-peck. Add `emerge`, climbing out of a water channel. |
| `SilverSpark.qvox` | 12 | A crackling mote of loose silver essence. Bright and small. `idle` loops a flicker. | A zap flare. |
| `RingKeeperWarden.qvox` | 80 | **Elite.** Mardra's foreman: a big man in a leather apron with a grey ring on his thumb and a meat cleaver. | Two clips: `ringpull` (raises the ringed hand, ring glowing) and `attack` (a slow overhead chop). |
| `Mardra.qvox` | 120 | **Act I boss: Goodwife Mardra Hobb, Brood-Mother of the Millpond.** Half woman, half moulting fowl. A goodwife's dress split at the back by grey wings shedding black feathers, bird-scaled legs, a long neck, a woman's face going to beak. Her right hand is fused around a large **grey ring** that glows. | `ringpull` (ringed hand out, glowing), `broodcall` (wings wide, head back), `attack` (wing buffet), `moult` (a feather storm burst, played below half health), `stagger` (hit on the ring), `death` (ring shatters). |

## 4. Buildings

Buildings stand in town or in a zone clearing. Ravenford's buildings currently wear the older code-built models, so the roles below are what each one should become.

| File | Where | Footprint × height | Look |
|---|---|---|---|
| `CrookedRaven.qvox` | Ravenford (now the tavern) | 6.5 × 6.5 × 7.5 | A two-storey timber-framed tavern with a sagging roofline, a hanging sign of a raven with a bent neck, warm windows, and ravens on the ridge. |
| `RookeryTower.qvox` | Ravenford (now the church) | 10 × 10 × 11 | A tall round stone tower with an open wooden loft at the top, rows of raven perches, and white-streaked walls. Edda's hut is at its foot. This is the town's landmark. |
| `ReevesHall.qvox` | Ravenford (now the warehouse) | 6.5 × 6.5 × 5.5 | A sturdy stone hall with a notice board of bounties beside the door, banners of the town's raven sigil, and barred lower windows. |
| `PellsChandlery.qvox` | Ravenford (now the store) | 6 × 6 × 6.5 | A narrow candle shop, with candles hung in the window, an outside stair up to **Jessa's garret** with one small window, and a crooked chimney. |
| `SennsNeedlehouse.qvox` | Ravenford (now the blacksmith) | 6.5 × 6.5 × 6 | A tailor's shop with bolts of grey cloth in the window, a dress form on the step, and a needle-and-thread sign. |
| `LanternAndMoth.qvox` | Ravenford (now the alchemist) | 5.5 × 5.5 × 5.5 | A small shopfront with stairs going *down* to a cellar door under a hanging shuttered lantern, moths painted on the sign, and a gambling table glimpsed inside. |
| `OrrasHospice.qvox` | Orra's Hill (now the church) | 10 × 10 × 11 | A grey stone hospice with long ward windows, the **Orran Eye** (an eye crossed by a vertical bar) carved over the gate, a bell cote, and a south wing with chained doors (locked until Act II). |
| `HobbsMill.qvox` | Hobb's Mill (now the ruined cottage) | 5 × 5 × 6, plus wheel | A stone-and-timber watermill with a big undershot wheel on the river side, flour sacks, an outside stair (where Lise stands), and a low **millrace door** with iron bands at water level. |

## 5. Props

Reeds and shrines are already code-built in `Source/Fenmarch.dk`. Swap in models if you want better ones.

| File | Where | Look |
|---|---|---|
| `FeatherShrine.qvox` | Orra's Hill | A roadside post shrine with a little roof, a crossbeam hung with black feathers and grey cloth strips, and tallow stubs at its foot. *(Code version exists.)* |
| `Gibbet.qvox` | Orra's Hill | A shrine gibbet: an empty iron cage on a post, a perch for Gallows Rooks. |
| `Reeds.qvox` | Fennick Water, millpond | Reeds and cattails with a black feather snagged in them. *(Code version exists.)* |
| `DuckPond.qvox` (decal-like) | Fennick Water | A floating mat of black feathers on water. |
| `TitheBracelet.qvox` | Drops, lore | A tin wristband stamped with the **Barred Eye** (an eye closed by a bar). Small. |
| `IronFrame.qvox` | Undercroft | An upright iron bearer frame with wrist shackles and silver wire running from the shackles into the floor. Empty version (the Hollowed Bearer has a full one). |
| `RingPedestal.qvox` | Undercroft, boss arena | A stone pedestal where every silver wire meets, with a socket in the top. The Dash rune is pried from it. |
| `WireRun.qvox` | Undercroft | A straight floor segment of silver wire for Silver Sparks to travel. Tileable. |
| `RavenPerch.qvox` | Ravenford roofs | A T-perch with two ravens, used as rooftop dressing. |

## 6. Item art (images, through `Tools/ItemArt`)

These are pictures, not sculpts. Each one becomes both the inventory icon and the dropped model. Add them to `Tools/ItemArt/items.json`.

| Item | Slot | Picture |
|---|---|---|
| Black Feather | Currency | A single glossy black feather with a blue-violet sheen. |
| Black Honey | Consumable | A small corked vial of black liquid whose bubbles sink *up*. |
| Tithe Bracelet | Lore | The tin band with the Barred Eye. |
| Jessa's Waterwalkers | Boots | Worn grey weaver's boots, waxed, with a silver thread stitched around the sole. |
| Edda's Quill Charm | Charm | A raven quill bound with red thread to a knuckle bone. |
| Marra's Thimble | Ring | A steel thimble worn as a ring, with a needle hole punched through. |
| The Ringwright's Grey Key | Quest | A plain grey ring with the Orran Eye engraved *inside* the band. |
| Mardra's Ring Shards | Charm | Three shards of a grey ring on a leather thong. |
| Greyneck's Quill | Amulet | One long grey-white quill on a chain. |
| Rune of Lattice Step | Rune | The Dash rune on a silver-veined stone, pried from a pedestal. |
| Ravenford Woodsman's Axe | Axe | Wren's axe: a plain bearded axe head and a dark ash haft wrapped in leather. |

---

**Priority if you go in order:** Wren rework → the four Ford Road enemies → Fennick Water → Orra's Hill → Mill enemies → Mardra and the Undercroft → NPCs → buildings. Enemies come first because they're on screen the most and already have a slot waiting in `Source/EnemyData.dk`.
