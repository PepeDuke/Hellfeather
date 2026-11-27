# Act II — Models to make

## Status (built from the Act II sheets)

Every model below now exists in `Assets/`, built from the sheets in `act2refs`. The Act II sheets show three views side by side (front, side, and a back or three-quarter view) with no dimension panel, so sizes come from the tables below and the footprint from the ratio of the views.

```
python Tools/Models/act2.py --import <folder of sheets>     crop the views (automatic; boxes drawn in Tools/Models/Inspect/Act2Crops.png)
python Tools/Models/act2.py                                  build every hull model
python Tools/Models/camp.py                                  build the recipe models
python Tools/Models/road.py                                  build the Hospice Road's recipes
python Tools/Models/enemies.py TitheHanged MoultingHound FeatherblightSwan   build the rigged enemies
python Tools/Models/gear.py SwanboneBuckler CarminesQuill    build the gear
python Tools/Models/inspect_models.py <Name>                 compare a model with its sheet
```

- **Crops.** `act2.py` finds each sheet's views by the empty columns between them and saves them to `Assets/Reference/Act2`. A sheet whose views come in another order is listed in `ORDER`, one whose views touch in `SPLITS`, one that paints an effect above the model (the Feather Fire's flame) in `CUT_TOP`, and one saved under another model's name in `ALIAS` (the Act II Carmine sheet is `RedWarden`, the boss, so Act I's nurse keeps her model). The `_Animation` sheets and the kit, material and layout sheets (`BellTentKit`, `CampMaterials`, `PilgrimsEncampment`…) are references only.
- **Recipes** (`camp.py`, on `kit.py` parts and the new camp parts: canvas with seams, patches and stains, bell and ridge tents, guy ropes, pennants, wheels, wattle, candles, badges, ribbons, hooped wagon covers, staved casks, plank boxes, cloth drapes, bottles and herbs): `PilgrimShrine`, `FeatherFire`, `WrensTent`, `PilgrimTent`, `PilgrimTentB` and `ChalkCircle`, and the props the camp's people stand at: `HesksWagon`, `TinkersCart`, `LongTable`, `CookPot`, `WaterBarrels`, `FeatherSack`, `RavenCage`, `TorchPole` and `TorchPoleCold`.
- **Road recipes** (`road.py`, on the camp and house parts plus gallows posts, iron straps, nooses, a hanged body, and `tilted` for a wreck): `RoadGibbet`, `RoadGibbetEmpty` and `DrownedCart`.
- **Rigged enemies** (`enemies.py`): `TitheHanged` on `Body`/`legs`/`human_clips` with a swaying walk; `FeatherblightSwan` on `Bird` with fanned, veined wings; `MoultingHound` on `Beast`, the new four-legged rig, with `beast_clips` (a trot, a crouch-and-lunge bite, a fall onto its side).
- **Camp people** (`people.py` rigs, with pilgrim parts: ragged hems, shawls, hoods up and down, rope belts, the Orran Eye badge, and `lower` to seat a standing figure): `PilgrimMotherHesk`, `TollyTinker`, `Pilgrim01`–`03` and `PilgrimSitting`, who sits on the long table's far bench. The camp's materials in `kit.py` are sampled from the CampMaterials and tent sheets.
- **Thornwick's recipes** (`thornwick.py`, on `house.py` parts plus dye runs, hung cloth, lean-tos, eye carvings and banners, hip roofs and charring): `ThornwickGate`, `TitheHouse`, `ClothiersGuildhall` and `ClothiersGuildhallBurnt` (gutted, the roof fallen in to its rafters), `ClothiersRow`, `ClothiersRowB`, `CloisterOfLooms` and `InscriptionLoom`. The gate and the Cloister are a little smaller than the sheets so the town's clearing holds every building, and buildings count as at most 30 columns tall for the strip kept clear behind them (`HellfeatherActTwoProps.Sight`). The loom is an open frame, so its outlines score below the bar though its parts match the sheet.
- **Hulls** (`act2.py` with `act1.py`'s builder): every other prop, building, person and enemy, as Act I's first models were. People get `idle` and `talk`; enemies get the five clips the game plays, by bending the hull. All pass `inspect_models.py`; MedicineCart and InkBlot are marked `loose`. As in Act I, the hulls that matter most (the south wing, the camp's other wagons, Corvin's bench) are the next candidates for recipes, and the other people and the enemies for the rigs.
- **Gear** (`gear.py`): `SwanboneBuckler` and `CarminesQuill`, with grips, worn through `HellfeatherWarrior.GearModel`.
- **Not built:** the pilgrim-cloak body variant (the `WarriorLeatherArmor` sheet), a hand-made rig for the rats (the hound's `Beast` rig fits them at a smaller scale), and new item pictures: Act II's items borrow the picture of the plain item they look most like (`HellfeatherItems.ActTwoLikeness`).
- **In the game:** `Source/ActTwoArt.dk` loads the props, `ActTwoTerrain.dk` places them (the encampment, the Hospice Road, the Shallows, Thornwick, the heath and the dungeon halls), `ActTwo.dk` places the people, `EnemyData.dk` lists the enemies.

Everything Act II in [Story.md](Story.md) needs that the game doesn't have a model for yet. That covers the Hospice Road, Thornmere Shallows, Thornwick, the Cloister of Looms, the Records Cellar and the South Wing, plus **the Pilgrims' Encampment**, Act II's hub (section 2). Act I's [Act1Models.md](Act1Models.md) describes the tools, and the same rules apply:

- **Enemies** go through `Tools/Models/enemies.py` on the rig: `Body`/`legs`/`human_clips` for people-shaped ones, `Bird`/`bird_clips` for swans and cygnets, and a new four-legged rig for the hounds and rats (see "New rig work" at the end). As in Act I, dropping a file named as below into `Assets/` is enough once its `EnemyKind` line exists in `EnemyData.dk`, and until then each kind borrows a stand-in at its own scale.
- **People** go through `Tools/Models/people.py` (`recipe=True`), are authored 70 rig voxels tall, and are scaled to the height `Cast.dk` gives `AddPerson`.
- **Buildings** go through `Tools/Models/buildings.py` with parts from `kit.py` and `house.py`. Tents, wagons and camp furniture are new parts (section 2.6), and they belong in a new `camp.py` beside `house.py`.
- **Small props and interiors** go through `Tools/Models/interiors.py` or a recipe of their own, at 0.0625-unit voxels like Ravenford's.

## Conventions

The conventions are the same as Act I's. They are repeated here so this file stands on its own.

- **Characters and creatures** are `.qvox` files with voxels 0.025 world units wide. Heights are in voxels; Wren is 78 (1.95 units). They face local +Z. `Height` in `EnemyData.dk` (and the height `Cast.dk` gives a person) must be the model's **box height**, the middle number the build prints, or the model sinks into the ground. The heights below are targets.
- **Enemy clips:** `idle` and `walk` loop; `attack`, `hit` and `death` play once. A generated attack lands on frame 2, and its wind-up frames add up to 270 ms, because `EnemyMoves.WindUp` stretches them to the move's wind-up.
- **Second moves.** Act II enemies get one or two moves. Today the game plays only the five clips above, so `attack` is always the **first** move listed. A second move's clip is named in the tables (`lash`, `scream`, `pin`…), so it already exists when `EnemyMoves.dk` learns to play it. Until then it is built but unused, like the Act I sheets' extra clips.
- **Soft control needs a readable pose.** Act II adds slows, roots of 2 s or less, and bleed. Any clip that roots or slows the player needs an anticipation pose that reads at camera distance: a raised noose, a chalk hand on the floor, a pole drawn back.
- **NPCs** stand still facing the camera, with one pose and an optional `idle` (and `talk` on the rig).
- **Buildings and props** use 0.0625-unit voxels. The door and the side that matters face +Z, toward the camera. Footprints are in world units.
- **Palette.** Act I was rain-grey and brown with black feathers. Act II keeps that and adds **dye colours**: Thornwick's madder red, woad blue and weld yellow, always dulled and wet, never bright. The South Wing is the exception: off-white smocks, grey stone and Carmine's **red**, the only saturated colour in the act. Swans are the only true white anywhere, which is why they look wrong.
- Palettes go from sRGB to linear light, as in Act I.

---

## 1. Player

Nothing new is required. Two optional additions:

| File | Description |
|---|---|
| `WarriorLeatherArmor.qvox` variant (optional) | A **pilgrim's cloak** variant for the Body slot, if Act II drops cloaks: a hooded grey wool cloak over the leather, a tin pilgrim's badge of the Orran Eye on the shoulder. Built by `player.py` as a variant like the two existing bodies. |
| `SwanboneBuckler.qvox` | II-1's reward, on `hand_l`. A small round buckler of pale boiled leather over a frame of swan bones, with the wingbone ends showing at the rim and one black feather tied to the boss. A recipe in `gear.py` with a `grip`, plus a line in `HellfeatherWarrior.GearModel`. |
| `CarminesQuill.qvox` | II-6's reward, an off-hand dagger: a long steel quill-pen nib the length of a forearm, with a red-lacquered grip and a tiny clicking cap. A `gear.py` recipe. |

## 2. The Pilgrims' Encampment (Act II hub)

### 2.1 What it is and why it's safe

Thornwick is a Red Cuff town with checkpoints at the gate, and after Act I the Cuffs know Wren's face. She can't sleep inside its walls, so Act II's hub is outside them: the **Pilgrims' Encampment**, a sprawl of tents and wagons around the **Pilgrim Shrine of Orra**, where the Hospice Road meets the Thornwick road on the shore of the Thornmere. The pilgrims are walking to Saint Orra's to be healed, and they don't know what the hospice does to the people it takes in. Pilgrim Mother Hesk runs the camp.

**Why it's safe.** Ravenford's ravens eat the black feathers. Here the pilgrims **burn** them. Every feather that drifts into camp is gathered and fed to the **Feather Fire**, a great brazier in front of the shrine, as an offering to Orra. Featherfall still falls over the camp, but the feathers never settle, and the fowl that follow them stop at the ring of torches. This is the camp's in-world reason to exist, as the ravens are Ravenford's.

**What the camp gives the player.** It provides the same services as Ravenford, so going "home" in Act II means going here:

| Service | Where in camp | Who / what | Replaces in Ravenford |
|---|---|---|---|
| Home waypoint and personal chest | **Wren's tent** | `HellfeatherResidence.PilgrimTent`; `MoveInto` brings the fire and the chest | Ravenford house |
| Waypoint | **The Feather Fire** at the shrine | Waypoint fire, lit from the start once Act II begins | The square's fire |
| Raven portal town end | Beside the Feather Fire | `HellfeatherPortals` town end moves here in Act II | Near the square |
| Potions, portals, charms | **Hesk's wagon** | Pilgrim Mother Hesk | Edda |
| Feather turn-in, raven favour | **The raven cage** | Edda's raven, sent by letter: feathers go back to Ravenford by bird | Rookery Tower |
| Coats, boots, mending | **The tinker's cart** | Tolly the Tinker | Marra |
| Runes (after II-6) | **Corvin's bench**, under an awning | Corvin Hale | Moth |
| Rumours, story beats | **The long table** by the cookfire | Vale at night (II-5, II-6), Matthew once (II-4) | Crooked Raven |

The **Inscription Loom** stays in Thornwick, as Story.md says, because unlocking it is part of II-2 and the Cloister. Corvin's bench gives the camp a second crafting place after II-6.

### 2.2 Layout

It's laid out like `Ravenford.dk`: a straight, level clearing, so offsets from its centre are world offsets. The player arrives up the screen from the road. The entrance is on the **+Z side, toward the camera**, and the engine keeps the road through it open. X and Z are world units from the camp's centre. Instead of Ravenford's 24-unit walls (radius 38), the camp is smaller and open: about **20 units across the working part**, inside an outer ring of about 26.

```
                         -Z (back, away from camera)
          Thornmere shore ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
          reeds, jetty, swan-scare poles     | drying racks
     ┌─────────────────────────────────────────────────────┐
     │  stake palisade + wagons (blocked, like the walls)   │
     │                                                      │
     │   [Corvin's bench]     ⛪ PILGRIM SHRINE OF ORRA      │
     │                         (stone, back-centre)         │
     │   [raven cage]          🔥 FEATHER FIRE  (waypoint)  │
     │                          ◯ portal spot               │
     │  [Wren's tent]                         [Hesk's wagon]│
     │                    ✦ cookfire + long table           │
     │  [pilgrim tents]                     [tinker's cart] │
     │      ×4–6           latrine screen ·  water barrels  │
     │                                                      │
     │  torch ring ·    ·    ·  ║ road ║  ·    ·    · torch │
     └──────────────────────────║      ║────────────────────┘
                               +Z (camera side): to the Hospice Road
                     road forks: west to Thornwick gate, south to Orra's Hill
```

Positions (world units from the centre, +Z toward the camera):

| Feature | X, Z | Notes |
|---|---|---|
| Pilgrim Shrine of Orra | 0, −9 | The landmark. Faces +Z. Everything gathers toward it. |
| Feather Fire (waypoint) | 0, −5 | The great brazier on its stone plinth, 3 units in front of the shrine steps. |
| Raven portal spot | 2.5, −3 | As `HellfeatherPortals.TownX/TownZ` are in Ravenford. |
| Cookfire and long table | −1, 2 | The social centre, a campfire prop (the `Fires.dk` campfire, logs). |
| Wren's tent | −9, 0 | Door flap faces +Z. Her residence door. |
| Hesk's wagon | 9, −1 | A covered wagon, tailboard down as a counter, facing +Z. |
| Tolly's cart | 8, 5 | A two-wheeled handcart with an awning and a grinding wheel. |
| Raven cage | −8, −6 | On a post beside a feather sack. |
| Corvin's bench | −5, −10 | Empty, under a folded awning, until II-6. Then it's set up with Corvin at it. |
| Pilgrim tents | ring at radius 11–15 | Four to six tents, in the left and right thirds, leaving the road clear. |
| Palisade and wagons | outer ring radius ~18 | Behind the camp (−Z) and on the sides. Blocked ground like Ravenford's walls. No wall on the +Z side, so walkers never hide behind it from the camera, the same reason Ravenford keeps a `SightStrip`. |
| Torch ring | radius ~17 on the +Z half | Eight to ten torch poles. `Fires.dk` lights them (they count toward its 12-fire budget, so use 6 live ones at most and unlit stubs for the rest). |
| Thornmere shore | Z < −18 | Water surface, reeds (`WetlandReeds`, `CattailReeds`), a short jetty, swan-scare poles. |

**Ground surfaces.** The camp needs two new `HellfeatherSurface` entries beside `Cobble`/`Earth`/`Mud`: **Trodden** (churned mud with straw laid over it, for the lanes between tents) and **Ash** (the grey circle around the Feather Fire, flecked with half-burnt black quills). The lane from the road to the fire is Trodden; the rest is `Earth` and grass.

**Light and mood.** It's dusk-warm, in contrast to the cold blue of the hospice road. Firelight is orange at the cookfire and white-hot at the Feather Fire, which also throws a faint **violet** tinge, the black feathers burning. Black quill-ash drifts up from the Feather Fire all the time (the `FallingFeathers` effect reversed, or a smoke style with dark motes).

**Events in camp.**
- **Featherfall** reaches the camp, but the feathers burn up within the torch ring: they fall, curl and go to embers before landing. That needs code in `Featherfall.dk`, not a model.
- **Swan Night** (II-1): Featherblight swans walk inland at night and stand at the torch ring, white in the dark, but never cross it. This is purely visual, and a strong image for the act.
- **The pilgrims leave.** After II-5, when Wren knows what the hospice is, she can tell Hesk. Then half the tents come down (a second `PilgrimTentStruck` model), and the camp is visibly emptier for the rest of the act. This is optional, a story flag only.

### 2.3 Encampment NPCs

All are 70–74 voxels tall unless noted, rig recipes in `people.py`.

| File | Who | Role | Look |
|---|---|---|---|
| `PilgrimMotherHesk.qvox` | **Pilgrim Mother Hesk** | Camp leader. II-1 giver. Potions, portals, charms (Edda's shelves). | A broad, weathered woman of sixty in many layers of undyed wool, a pilgrim's grey hood down, a staff hung with tin badges from every shrine on the road. A tin Orran Eye on a cord. Soot on her hands from feeding the Feather Fire. Kind, tired, sure of the hospice. |
| `TollyTinker.qvox` | **Tolly the Tinker** | Coats, boots and mending (Marra's shelves). | A wiry, quick man in a patched leather apron over a dyer's-red shirt faded to pink, a ring of keys and awls on his belt, spectacles pushed up on his head. Sleeves rolled, a burn scar on one forearm. Sells things he can't quite explain how he got. |
| `CorvinHale.qvox` | **Corvin Hale, the Ringwright** | Rune vendor after II-6. Also the South Wing prisoner before that, so the model needs two poses or two files (`CorvinHaleChained.qvox`, see 3.6). | An old, thin man with a jeweller's hands, white stubble, and burn-pocked fingertips from years of ring-work. A grey ring-maker's apron, hospice smock under it, a loupe on a band over one eye. At the bench: one hand resting on a tray of grey rings he refuses to finish. |
| `EddaRaven` (reuse `Raven.qvox`) | **Edda's raven** | Feather turn-ins by post | Uses the existing raven, perched on `RavenCage.qvox`. No new model; a person entry in `Cast.dk` so it can be talked to. |
| `Pilgrim01..03.qvox` | **Pilgrims** (ambient) | Dressing; one or two say a line | Three variants on the shared `Body`: an old man on a crutch with a bandaged eye; a mother with a coughing child on her hip (child part of the model); a young man with a tithe bracelet he doesn't know the meaning of. Grey and undyed wool, rope belts, tin Orran Eye badges. `idle` only. |
| `PilgrimSitting.qvox` | Pilgrim at the long table | Dressing | One static seated figure, eating from a bowl. Built as a static like `JessaBed`. |

**People who visit the camp** (models exist; only `Cast.dk` placement is new): **Sister Vale** at the long table at night before II-5 and II-6, and **Matthew** once, after II-4, standing by the Feather Fire with his shadow leaning toward it.

### 2.4 Encampment buildings

0.0625-unit voxels, door or important side facing +Z, `camp.py` recipes.

| File | Footprint × height | Look |
|---|---|---|
| `PilgrimShrine.qvox` | 7 × 5 × 7 | **The Pilgrim Shrine of Orra**, the camp's landmark. A roofless chapel front of grey fieldstone: three steps up, a pointed arch, and inside it a weathered statue of Orra with a stone bar across her eyes (the **Orran Eye** shape). Feathers, tin badges, ribbons and wax tablets are wedged into every crack. Candle stubs line the steps. One side wall has fallen, and pilgrims have patched it with wattle and canvas. It must read at the hub's camera distance. |
| `FeatherFire.qvox` | 2.5 × 2.5 × 2 | A wide iron fire-basket on a square stone plinth, its bowl heaped with half-burnt black quills. Iron rakes lean against it, and there's a sack of gathered feathers beside it. The `Fires.dk` flame sits in the bowl. It should look like it could be a waypoint fireplace, because it is one. |
| `WrensTent.qvox` | 4 × 4 × 3 | Wren's residence. A ridge tent of oiled, patched canvas on two poles, guy ropes pegged out, the door flap tied back on the +Z side, with a glimpse of a cot inside. Her axe-sharpening stone and a bucket by the door. Plainer than the pilgrims' tents, a thief-taker's. |
| `PilgrimTent.qvox` | 3.5 × 3.5 × 2.5 | A pilgrims' tent: a low bell tent of grey wool felt, smoke-stained at the peak, a strip of shrine ribbon tied to the pole tip. Make two variants by colour and a sagging side (`PilgrimTentB.qvox`) so the ring doesn't repeat. |
| `PilgrimTentStruck.qvox` | 3.5 × 3.5 × 0.8 | The same tent taken down: canvas folded, poles bundled, a bare ring of flattened straw. For "The pilgrims leave". |
| `HesksWagon.qvox` | 5 × 2.5 × 3.5 | A covered wagon with a hooped grey canvas top and big spoked wheels. The tailboard is down as a counter with jars, bundled charms and portal scrolls on it, and a lantern hangs from the hoop. A pilgrim's staff of tin badges leans on the wheel. |
| `TinkersCart.qvox` | 3 × 2 × 2.5 | A two-wheeled handcart under a striped awning in faded dye colours. Racks of boots and coats hang from the awning poles, there's a foot-driven grinding wheel, and a tin sign of a needle and hammer. |
| `CorvinsBench.qvox` | 3 × 2 × 2.5 | A ringwright's bench under a canvas awning: a vice, a tiny anvil, a crucible on a brazier, tongs, a tray of grey rings, a loupe. Build a second, packed-up state, `CorvinsBenchPacked.qvox` (awning folded, tools in a crate), for before II-6. |

### 2.5 Encampment props

| File | Look |
|---|---|
| `RavenCage.qvox` | A tall wicker cage on a post, door open, with a perch inside and a raven-sized gap. A small sack of feathers hangs on the post and a tin cup of water sits on top. Edda's raven sits on it. |
| `LongTable.qvox` | A trestle table of rough planks with benches each side, bowls, a bread loaf, a pot. Long side along X. |
| `CookPot.qvox` | An iron pot on a tripod over the campfire, ladle in it. Sits on the existing campfire. |
| `TorchPole.qvox` | A tall pole with a pitch-soaked rag torch, a strip of shrine ribbon below it. A lit version for `Fires.dk`, an unlit stub version (`TorchPoleCold.qvox`). |
| `StakePalisade.qvox` | A tileable 4-unit section of sharpened stakes lashed with rope, a few black feathers caught in it. Corners can be wagons instead. |
| `CampWagon.qvox` | A plain uncovered cart, tipped on its side, part of the outer ring. Two variants by angle. |
| `DryingRack.qvox` | A rack of poles hung with grey laundry and dyed rags (dull red, blue, yellow from Thornwick), by the shore. |
| `SwanScare.qvox` | A pole on the shore with tin badges and a bundle of white swan feathers hung on it to frighten swans. It doesn't work. |
| `Jetty.qvox` | A short rotting jetty of planks on posts, 5 long, one tied punt. |
| `WaterBarrels.qvox` | Reuse `Barrels.qvox` where possible. Add a version with a ladle and a wet ring around it. |
| `LatrineScreen.qvox` | A woven wattle screen. Dressing at the camp's edge. |
| `OfferingPile.qvox` | Small dressing for the shrine steps: candle stubs, a wax tablet, a tin badge, a few feathers, a child's shoe. |
| `FeatherSack.qvox` | An open sack of gathered black feathers, for beside the Feather Fire and the raven cage. |

Interior props for **Wren's tent** reuse the Act I interior set: `Cot`, `Chest` (her personal chest), `Stool`, `Washstand`. The fire is a new `Brazier.qvox`, a small iron pot-brazier on three legs, because a tent can't have the `Hearth`. It's the Home waypoint's fire inside. The tent interior is a small `Interiors.dk` level: about 4 × 4, canvas walls (a new `HellfeatherSurface.Canvas`, or `Plaster` recoloured), a straw floor.

### 2.6 New kit parts (`camp.py`)

Tents, wagons and stakes aren't in `house.py`. The parts are reused across every camp building and the Act II wilds (pilgrim camps along the road), so they're worth building once:

- **Canvas**: a draped sheet between ridge or hoop and pegs, with sag between supports, patch rectangles, and a stain gradient toward the top (smoke) and bottom (mud).
- **Bell tent**: a cone of canvas around a centre pole, with a door flap that can be open or closed.
- **Ridge tent**: two poles, a ridge line, and sloped canvas sides.
- **Guy ropes and pegs**: thin lines from the canvas to the ground.
- **Wheel**: spoked, with a size parameter (for wagons, carts and the grinding wheel).
- **Hoop cover**: canvas over hoops for the covered wagon.
- **Stake**: a sharpened pole with a lashing band.
- **Materials** added to `kit.py`: canvas (grey, oiled grey), wool felt, wicker, pitch, tin, dyed cloth (dull madder red, woad blue, weld yellow), and quill-ash. As Act I's notes say, each model's file lists only the colours it uses, since there are only 92 symbols.

---

## 3. Act II NPCs (outside the camp)

| File | Who | Where | Look |
|---|---|---|---|
| `MistressAgnet.qvox` | **Mistress Agnet**, head of the Cloister of Looms | Cloister Library | A tall, spare woman in her sixties in charcoal cloister robes with a loom-master's chain of tiny brass shuttles, white chalk-dust hands, and spectacles on a cord. A thick ledger held to her chest. Gentle face. The model should feel kind, which is the point: she expelled Jessa "compassionately". |
| `CloisterNovice.qvox` (ambient) | Students | Cloister | The Novice Weaver enemy's look without the fear: grey robes, chalk-white hands, a slate. Two or three poses. Could share the enemy's rig recipe. |
| `ThornwickDyer.qvox` (ambient) | Townsfolk | Thornwick | Dyers with forearms stained to the elbow in madder red or woad blue, leather aprons, wooden clogs. Two variants by stain colour. |
| `TitheClerk.qvox` | Clerk at the Tithe-House | Thornwick | A pinched man in a black clerk's coat with Barred Eye sleeve-guards, an ink pot on a cord, a ledger. |
| `ThornwickGateCuff.qvox` | Checkpoint Cuffs | Thornwick gate | Reuse `Cuffman.qvox` with a toll satchel. NPC pose while talking, enemy clips if the Shakedown turns into a fight. Possibly no new model. |
| `CorvinHaleChained.qvox` | **Corvin Hale**, prisoner | South Wing | Corvin (2.3) in a stained hospice smock, chained by one ankle to a workbench in a cell, mid-work on a grey ring. A static pose; the bench is part of the model. |
| `SisterCarmine.qvox` (rework) | **Sister Carmine** | Hospice gate (Act I) and Relay Chapel (boss) | The existing model gets **boss clips**; see 4.6. |

## 4. Enemies

Heights are targets in rig voxels; the box height the build prints goes in `EnemyData.dk`. "Attack clip" is the **first** move. "Second clip" is built now and played when `EnemyMoves.dk` supports a second move.

### 4.1 The Hospice Road

| File | Height | Look | Attack clip | Second clip |
|---|---|---|---|---|
| `TitheHanged.qvox` | 76 | A pilgrim cut down from a gibbet: rope still around the neck with a long trailing noose end, head tilted hard to one side, grey pilgrim wool, tithe bracelet on both wrists, bare feet. Swaying gait: `walk` sways side to side as much as it moves forward. Add `rise` (getting up from lying on the road) when the game can play it. | `lash`, used as `attack`: whirls the noose overhead twice, then whips it out at mid range. The slow. | — |
| `MoultingHound.qvox` | 44 (about 60 long) | A lean wild dog with mangy grey-brown fur, black quills pushing out along the spine and shoulders, ribs showing, lips back. Four-legged rig. | `bite`: a low lunge and a snap that draws bleed. | — (flanking is behaviour, not a clip) |
| `HighwayCuff.qvox` | 76 | A Red Cuff toll-taker: a road cloak over the gambeson, red cloth at the cuffs, a fat coin satchel at the hip, a brass horn on a baldric, arming sword. Heavier and better-fed than a Cuffman. | `attack`: a sword cut that snatches at the satchel side (Tithe Strike, steals gold). | `horn`: plants his feet, raises the horn to his mouth, cheeks out. It needs a long readable hold, since it's the "kill him first" cue. |
| `GallowsRook.qvox` | 44 | *(exists)* Larger flocks; Dive now bleeds. No model change. | — | — |
| `RoadGibbet.qvox` (prop) | — | The Act I `Gibbet` with a hanged figure in it, and an empty variant with a cut rope. That's where the Tithe-Hanged come from. | | |

### 4.2 Thornmere Shallows

| File | Height | Look | Attack clip | Second clip |
|---|---|---|---|---|
| `FeatherblightSwan.qvox` | 96 | A big mute swan, pure white except black veins running out from the wing roots across the feathers like ink in water, and eyes like oil (a rainbow sheen on black). Neck held in a perfect S. `idle` and `walk` should be *beautiful*: slow, gliding, the neck barely moving. Add `swim`. | `fan`: the wings rise and spread wide, then sweep forward, throwing a cone of feathers (Feather Fan). | `gust`: the wings beat down once, hard, chest forward (Wing Gust, knockback). |
| `SwanMatriarch.qvox` | 130 | **Unique (II-1).** A Featherblight Swan grown huge and old, more black than white now, with veins on the neck and face, a tattered wing edge, and one leg ringed with an iron band (a hospice pinion ring). | `fan` | `gust`, plus `call` (head up, honk, cygnets come). |
| `CygnetBrood.qvox` | 30 | A grey downy cygnet, oversized feet, black quill tips pushing through the down at the wings, beak open hissing. Swarms, so keep it cheap like `Duckling`. | `peck` | `hiss`: neck stretched, beak wide. It calls the nearest swan. |
| `ReedDrowner.qvox` | 74 | A drowned pilgrim wrapped in reeds and pondweed, skin grey-green, hair over the face, tin badge on the chest. Most of the time only a pale hand above the water: `idle` is the **submerged** pose (hand and top of head), and `walk` is rising and wading. | `drag`: the arm shoots out, grabs low and hauls back (the 2 s root). | — |

### 4.3 The Cloister of Looms

| File | Height | Look | Attack clip | Second clip |
|---|---|---|---|---|
| `LoomWight.qvox` | 78 | A padded cloth practice dummy on a wooden post-frame, walking stiffly on two pegs. It's covered in chalked student inscriptions, half of them crossed out. On the chest is a large inscription disk that glows **blue or red** before each attack. The glow should be a separate, recolourable part, or two clip sets, so the game can show which flavour is coming. | `push`: blue glow, arms stiffly shove out. | `burst`: red glow, the disk flares and the body jerks back. |
| `NoviceWeaver.qvox` | 70 | Young and frightened, in grey cloister robes, with chalk-white hands to the wrist, a satchel of chalk sticks, and a tiny red Cuff patron's ribbon on the sleeve. Holds back, shoulders hunched. | `dart`: one hand flicks forward (Projection Dart). | `chalk`: kneels and draws a circle on the floor with one chalked hand (Hold Mark). |
| `AnimatedShuttle.qvox` | 14 (about 30 long) | A boat-shaped wooden loom shuttle, polished by hands, flying point-first, with a spool of silver thread trailing out of it. `idle` hovers and wobbles. The thread *between* shuttles is drawn by the game, not the model. | `dart`: a fast straight lunge. | — |
| `InkBlot.qvox` | 24 (about 40 wide) | A crawling puddle-blob of glossy black ink with loose letters (pale parchment-coloured glyphs) drifting inside it. `walk` is a slow smear. Add `split` (it divides into two). The game scales it down for the small blots, so one model is enough. | `smear`: it heaves up and slaps down. | — |
| `FailedLoom.qvox` | 110 (about 90 wide) | **Unique.** An upright practice loom of dark wood, walking on its frame-legs like a spider: warp threads strung through it half-woven into a figure that never finishes, shuttles circling it, and inscription chalk all over the beams. | `weave`: the frame shudders and the heddles slam, and a thread figure starts in the warp. That's its summon. | `beam`: the breast beam swings forward like a ram. |

### 4.4 Saint Orra's: Records Cellar

| File | Height | Look | Attack clip | Second clip |
|---|---|---|---|---|
| `ArchiveRat.qvox` | 14 | A rat with ink-stained fur and a scrap of paper in its teeth, eyes that catch the light. The swarm is many of these, so it must be the cheapest model in the act. Four-legged rig, at a smaller scale. | `gnaw` | — |
| `CellarWatchman.qvox` | 76 | A Red Cuff in a long grey coat with a hooded iron lantern held out at arm's length (the light cone comes from it; give it a `lantern` socket) and a cudgel. A scarf over the nose against the dust. | `attack`: a cudgel hit (slows). | `alarm`: lantern raised high, mouth open. |
| `ClerkShade.qvox` | 72 | The ghost of a clerk: translucent grey-blue, sleeve-guards, a stooped back, ink running down from both eyes like tears, a big brass stamp in one hand. Hovers with the feet trailing off. `idle` stamps endlessly at nothing. | `stamp`: winds the stamp back and throws a seal (it marks the player DECEASED). | — |

### 4.5 Saint Orra's: South Wing

| File | Height | Look | Attack clip | Second clip |
|---|---|---|---|---|
| `StitchedPatient.qvox` | 82 | A patient in a stained smock, sewn to an iron frame at the shoulders and hips, carrying it on the back like a cross, which is why the box is taller. The stitches are visible thick black thread. Slow, bent `walk`. The frame is part of the model. Add `freed` (thread cut, the frame falls, the patient drops to the knees) like the Hollowed Bearer's. | `slam`: lifts both arms with the frame and brings it down overhead. | — |
| `WardScreamer.qvox` | 72 | A thin patient with the mouth sewn half shut, eyes stretched too wide, hands pressed over the ears, gown hanging off one shoulder. Backs away in `walk`. | `scream`: the head tips back and the chest heaves; the stitches strain (Muffled Scream). | — |
| `HospiceOrderly.qvox` | 92 | A huge man in a grey-stained white smock and a leather apron, sleeves rolled on forearms like hams, carrying a long restraint pole with a leather loop on the end. Shaved head, no expression. | `pin`: the pole drawn back two-handed, then a long lunge (the root). | `slam`: a shoulder body slam. |
| `OrderlyBrann.qvox` | 104 | **Unique.** A bigger orderly with a heavy restraint chair, straps dangling, carried on one arm as a shield. A ring of keys and a bloodied smock. | `attack`: the chair swung like a club. | `pin` (as the Orderly). |
| `LatticeHost.qvox` | 74 | A patient with black veins spreading from a mark behind the ear across the neck and face, and skin like cracked porcelain (pale grey with dark crack lines). Walks straight, arms a little out, reaching. | `touch`: both hands reach and grab (Tithe Rot). | — |

### 4.6 Boss: Sister Carmine, the Red Warden

| File | Height | Look | Clips |
|---|---|---|---|
| `SisterCarmine.qvox` (rework to boss) | 74 (consider 84 for the fight, scaled up) | The existing Act I model: grey habit, starched red wimple, red apron, very red lips, steel pen. For the fight she gets **red thread** spooled on her belt and a few needles in the apron bib, and her face stays smiling. The pen clicks in every `idle` loop. | `idle` (upright, the pen clicking), `walk` (brisk, never hurried), `attack` = **Needle Volley** (the pen hand flicks out three times, fanning), `bind` = **Bind Stitch** (draws a long red thread out of the apron and casts it like a line), `draw` = **You Become My Problem** (arms open, red threads run in from every direction to her chest, head back), `hit`, `death` (she sits down on the chapel floor, primly, and stops). |
| `RelaySocket.qvox` (prop) | — | The **relay chapel's ring socket**: a waist-high stone font with the Barred Eye carved on it, silver wire running from it into every wall, and a grey-ring-shaped hollow in the top. A cousin of `RingPedestal`. | |
| `PatientFrame.qvox` (prop) | — | The chapel's patient frames: `IronFrame` with red thread instead of silver wire, with a stitched patient in it. They're interactable for the Severing mid-fight. Build an empty version too. | |

---

## 5. Buildings

| File | Where | Footprint × height | Look |
|---|---|---|---|
| `ThornwickGate.qvox` | Thornwick | 12 × 4 × 8 | The town's gatehouse: a stone arch between two squat towers, a portcullis raised. Red Cuff banners with the Barred Eye, a toll booth hut beside it, a chained bar across the road for the **Checkpoint Shakedown**. |
| `TitheHouse.qvox` | Thornwick | 8 × 7 × 8 | **Thornwick Tithe-House.** A narrow, tall stone counting-house with a heavy oak door under a carved **Barred Eye**, barred windows on the ground floor, a Red Cuff barracks wing to one side, and a ledger-room window lit late. |
| `ClothiersGuildhall.qvox` | Thornwick | 8 × 7 × 9 | **The Clothiers' Guildhall** with **Journeyman & Vale, Factors** above it. A broad timber-framed guildhall with a jettied upper floor, bolts of dyed cloth hung from the beams, and an outside stair to a side door under an old painted sign, *Journeyman & Vale, Factors*, whose paint is older than the guild's. Needs a burnt variant, `ClothiersGuildhallBurnt.qvox` (the upper floor charred, the windows black), for after **The Burning Archive**. |
| `InscriptionLoom.qvox` | Thornwick, by the Cloister gate | 4 × 3 × 4 | **The Inscription Loom**, the crafting station. A great upright loom of dark wood whose warp is silver thread, set under an open-sided timber shelter. Rune-stones are slotted into the beam, and a chalk circle is on the floor in front of it. |
| `ClothiersRow.qvox` ×2–3 | Thornwick | 6 × 6 × 7 | Dyers' houses: timber and plaster, dye-stained walls (red streaks below the windows), cloth banners hung across the lane, vats in the yards. Variants for the street. |
| `DyeVats.qvox` (prop) | Thornwick | 3 × 2 × 1.5 | Three sunken stone vats, one red, one blue, one yellow, with a pole and wet cloth hanging over the edge. |
| `CloisterOfLooms.qvox` | Cloister of Looms (exterior) | 14 × 12 × 12 | A grey stone school around a cloister walk: a bell tower capped with a shuttle-shaped weathervane, long practice-hall windows, the Orran Eye over the gate, and a library wing with tall narrow windows. |
| `HospiceSouthWing.qvox` | Orra's Hill | (attaches to `OrrasHospice`) | The Act I hospice's south wing, **unchained** for Act II: the doors open, the chains hanging cut. A swap model for the wing, or a variant of the whole `OrrasHospice` in `buildings.py`. |
| `PilgrimCampRoadside.qvox` | Hospice Road | 6 × 6 × 3 | A small roadside pilgrim camp for the wilds: two tents from `camp.py`, a cold firepit, bedrolls. Tithe-Hanged rise near these. |

## 6. Interiors and dungeon props

Built with `interiors.py` at 0.0625 voxels, placed by `Interiors.dk` or `Undercroft.dk`-style level code.

### Cloister of Looms

| File | Look |
|---|---|
| `PracticeLoom.qvox` | A smaller student loom, half-woven, with chalk marks. Several fill the practice halls. |
| `Lectern.qvox` | A slanted reading desk on a column with a chained book. |
| `Bookshelf.qvox` / `BookshelfEast.qvox` | Tall library shelves of ledgers and scrolls, with a library ladder. (Turned variants, as in Act I's interiors.) |
| `ExpulsionCabinet.qvox` | A tall cabinet of narrow drawers, each labelled. Jessa's file is in it (II-2). |
| `ChalkCircle.qvox` (flat) | A flat chalk inscription circle on the floor, for the tutorial and Hold Mark decals. |
| `ThreadSpools.qvox` | Racks of thread spools, some silver. |

### Records Cellar

| File | Look |
|---|---|
| `RecordShelf.qvox` / `RecordShelfEast.qvox` | Floor-to-ceiling shelves of grey boxes, each with a paper label, some fallen. *Shelves of boxed lives.* Tileable along their long side. |
| `TransferredCabinet.qvox` | **The DECEASED — TRANSFERRED cabinet** (II-5). An iron filing cabinet, painted grey, a stencilled label, one drawer pulled out with files fanned. |
| `ClerksDesk.qvox` | A high clerk's desk with a stool, ink, stamps and a spike of receipts. The Clerk-Shades haunt these. |
| `BoilerHatch.qvox` | The boiler room hatch Vale opens as a distraction: an iron door in the wall with a pressure wheel and steam stains. |

### South Wing

| File | Look |
|---|---|
| `WardBed.qvox` / `WardBedEast.qvox` | An iron hospice bed with leather restraints and a thin grey blanket. Some occupied (static patient), some empty. |
| `StitchFrame.qvox` | The upright iron frame patients are sewn into: `IronFrame`'s cousin with needles and a spool of black thread hung on it. Empty. |
| `CellDoor.qvox` | An iron-banded cell door with a slot, for the hidden cells of **The Four Notes**. Open and closed variants. |
| `RestraintChair.qvox` | A heavy wooden chair with leather straps. Dressing, and Brann's shield. |
| `MedicineCart.qvox` | A wheeled tray of brown bottles, steel tools and a basin. |
| `WardCurtain.qvox` | A hanging curtain screen on a rail, stained. |

### Hospice Road and Thornmere (wild props)

| File | Look |
|---|---|
| `RoadGibbet.qvox` | See 4.1. |
| `RoadsideShrine.qvox` | Reuse `FeatherShrine.qvox`; add a tin-badge variant. |
| `SwanNest.qvox` | A great heaped nest of reeds and black-veined white feathers on the shore. The Swan Matriarch's has broken eggshells. |
| `DrownedCart.qvox` | A pilgrim cart half sunk in the shallows, wheels up. |

## 7. Item art (images, through `Tools/ItemArt`)

Pictures, not sculpts. Each one becomes both the inventory icon and the dropped model. Add them to `Tools/ItemArt/items.json`.

| Item | Slot | Picture |
|---|---|---|
| Swanbone Buckler | Shield | A pale leather buckler on a frame of swan bones, a black feather tied to the boss. |
| *Laws of Weaving* | Tome / lore | A thick grey-bound book with the Orran Eye stamped in silver on the cover, a chalk-dusted thumb mark. |
| Blank Rune | Crafting | A smooth flat grey stone with a faint silver vein and no mark. |
| The Tithe Ledger | Quest | A black ledger with the Barred Eye on the spine, codes like C-R17 visible on an open page. |
| The Bent Quarrel | Trinket | A crossbow quarrel bent in the middle, its head flattened as if it hit a wall. |
| Lise's File | Quest / lore | A thin folder tied with string, a scrawled *L. Hobb*. |
| Hospice Key | Quest | A long iron key with an Orran Eye bow. |
| Carmine's Quill | Off-hand | The steel quill-pen dagger, red grip. |
| Pilgrim's Badge | Charm (optional drop) | A tin Orran Eye on a cord, the kind every pilgrim wears. |
| Orran Chalk | Consumable | A stick of white chalk wrapped in a strip of grey cloth with the Orran Eye. |

---

## 8. New rig and engine work this list implies

These aren't models, but the models above assume them:

- **A four-legged rig** in `figure.py` (or `enemies.py`) for the Moulting Hound and Archive Rat, and later the Crag Hound, Quill-Horn Goat and Gutter Rats of Acts III–V. Body, four legs with a trot cycle, neck and head, tail.
- **Second-move clips**: `EnemyMoves.dk` plays only `attack` today. Act II has the first enemies whose two moves look different (`horn`, `gust`, `chalk`, `alarm`, `bind`).
- **Recolourable glow parts** for the Loom-Wight's blue/red disk. Otherwise build two models, or two sets of attack clips.
- **Threads drawn between models** (Animated Shuttle pairs, Bind Stitch, Carmine's draw): an effect or line in code, not a model.
- **`camp.py`** with the tent, canvas, wheel and stake parts (2.6).
- **The encampment module**: an `Encampment.dk` terrain module like `Ravenford.dk` (Trodden and Ash surfaces, the open +Z side, the shore), a `HellfeatherResidence.PilgrimTent` entry with its tent interior, a waypoint at the Feather Fire, the raven portal's town end moving there for Act II, merchant entries for Hesk and Tolly (and Corvin after II-6), and Featherfall burning out inside the torch ring.

## 9. Story.md changes this implies

The encampment adds to Story.md rather than contradicting it. To keep the two files in step:

- Add **The Pilgrims' Encampment** to Act II's **Zones** as *Town (hub)*, around the Pilgrim Shrine of Orra, and change Thornwick from "Town (secondary hub)" to a town zone with the Tithe-House, the Guildhall, the Cloister gate and the Inscription Loom.
- Corvin Hale joins **the encampment** as rune vendor after II-6, not Thornwick.
- New characters: **Tolly the Tinker** (camp vendor). Hesk becomes a vendor as well as II-1's giver.
- The Feather Fire is the camp's reason to be safe, as the ravens are Ravenford's. Feather turn-ins continue by Edda's raven.

---

**Priority if you go in order:** the encampment (shrine, Feather Fire, Wren's tent, Hesk, two pilgrim tents, the torch ring) so Act II has a home → Hospice Road enemies (Tithe-Hanged, Moulting Hound with the four-legged rig, Highway Cuff) → Thornmere (swans, cygnets, Reed Drowner, the Matriarch) → Thornwick buildings → Cloister enemies and props → Records Cellar → South Wing and Carmine's boss rework → the rest of the camp (Tolly, Corvin's bench, struck tents) → item art. As in Act I, enemies come before the remaining buildings, because they're on screen the most.
