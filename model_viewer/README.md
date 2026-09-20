# Blue Archive model viewer (PoC)

`export_models.py` pulls character models out of the game's Unity asset bundles
and writes one self-contained `.glb` per character into this directory: skinned
meshes, embedded textures, the bone hierarchy and every animation clip that moves
the character. `viewer.html` displays them with the
[ModelViewer gadget](https://dev.miraheze.org/wiki/Template:ModelViewer/doc).

```sh
# what can be exported (~305 bundles, each with the wiki name it is filed under)
python export_models.py --list

python export_models.py airi_original aris_original
python export_models.py "Aru (New Year)"               # wiki names work too
python export_models.py --all
python export_models.py --all --jobs 4
python export_models.py --overwrite airi_original      # regenerate an existing model
python export_models.py --overwrite --no-animations airi_original   # bind pose only, ~1/3 the size

# the viewer needs HTTP; file:// blocks the fetch of models.json
python -m http.server 8000   # then open http://localhost:8000/viewer.html
```

Existing `.glb` files are skipped unless `--overwrite` is supplied. `--jobs N`
sets the number of concurrent worker processes; it defaults to
`max(1, hardware threads - 4)`. Use `--jobs 1` for sequential exports.

Each run updates `models.json`, including skipped models, which `viewer.html` reads to build its model
dropdown. It maps each file to its mtime, which the viewer appends to the model's
URL so a re-export is not hidden behind a browser's cached copy of the old one.
The animation dropdown comes from the clips inside the selected `.glb`, so no
extra files are needed. Clips are ordered for browsing: `Cafe_Reaction` first,
then the other shared cafe and formation clips, EX/cutin clips, and the usual
combat states. Character-specific clips follow alphabetically. The viewer opens
`Cafe_Reaction` when it is present.

## What it does

**Names.** Bundles are named for the dev's own character codes — `ch0069`,
`aru_newyear`, `shiroko_ridingsuit` — so each model is written out under the
wiki's name for that character instead: `Mika.glb`, `Aru (New Year).glb`. The
lookup is `json/devname_map.json` and `json/devname_map_aux.json`, the tables
[the wiki repo keeps](https://github.com/electricgoat/bluearchivewiki/blob/master/translation/devname_map.json)
and `update.py` refreshes, read the same way `utils.dev_name_to_canonical_name`
reads them for the rest of the bot. A few bundles hold an alternate rig under a
suffix the tables do not carry — a cut-in, a story scene, a mech — which becomes
a second parenthesis: `Arisu (Battle) (Carrier).glb`. A bundle in no table keeps
its own name; of the ones that export, that is `ch0061`, `sm030001` and
`sm032601`. The bundle name is still what the CLI takes and what the exporter works
from internally, since it names the prefabs to walk and the prefix to strip off
clip names; `--list` prints both, and either one can be passed as an argument.

**What counts as the character.** A character's bundles carry far more than the
character: every effect it can spawn ships alongside it, and those prefabs have
meshes of their own — rocks, sea waves, beams, whole cut-in backdrops, most of
them textured from bundles nothing here loads. The AssetBundle index sorts the
two apart, filing the artists' fbx files under `<character>/Model/` and the
effects under `<character>/Effect/`, but `Model/` still covers props the
character never wears: Cherino ships 130 breakable wall panels for her cut-in,
Neru a squadron of drones. So the exporter takes the two prefabs named after the
bundle — `<name>_Mesh` and, as a fallback, `<name>_Halo` — and walks those hierarchies instead of
sweeping every renderer in the set. Three characters name the rig something else
and fall back to the `Model/` prefab with the most skinned renderers, which is
the body every time. A clip left driving nothing — a camera track, or an
animation written for a prop rig — is dropped along with the geometry it
belonged to.

**The halo.** The runtime character prefab supplies a `HaloRoot` subtree with
the intended mesh, material, position and scale. The exporter reads it from
`character-<name>-_mxload-*` bundles and follows references into other bundles,
so costumes can reuse their base character's halo without a name mapping.
Only that subtree is imported from the runtime prefab; its other meshes and
clips are not exported. When it is available, halo copies in the model FBX
hierarchies are omitted to avoid duplicates.

The runtime halo's follower component supplies a `FollowTarget` bone and
`TargetRelativePosition` / `TargetRelativeRotation`. The exporter attaches the
halo to that bone with those offsets, rather than preserving a saved world
position that may be stale. It follows the bone directly; the game's smoothing
and clamping are not simulated. Without follower settings it attaches to
`Bip001 Head`, preserving the rest placement. If the runtime prefab has no renderable
`HaloRoot`, the exporter retains the original model-based discovery: embedded
halos and `Model/` prefabs with a `_halo` suffix. There are no character-specific
exceptions.

**Props the pose does not use.** A rig carries more than the character wears:
Hoshino's shield exists for the length of her EX, Cherino rides a tank in one
cut-in, Hanae has a rabbit that hops around for a skill. Each rides along on
bones of its own, and a clip that does not use them leaves those bones at rest,
which parks the prop wherever the artist modelled it — inside the character, or
off beside her. Nothing in the bundles says outright which clip has which prop
out, but a clip binds every transform of the arrangement it was written for,
still ones included, so the bindings say it for them: a mesh the default clip
— `Cafe_Reaction`, or the first clip in the file — binds nothing of is a prop,
and the clips that do bind it are the clips that have it out.

Props are flagged `{"optional": true}` in their node's glTF `extras`, which
`data-hide-parts="optional"` in `viewer.html` switches off, along with a group
key the clips that want it back name in their own `extras` as `show`. The
grouping is there because a prop is rarely one mesh — Hanae's rabbit is a body
and two eyes on one rig, and a clip that binds the body but holds the eyes still
would otherwise leave a rabbit with no eyes. A group is the whole subtree the
prop hangs under, climbing until the next step up would swallow something the
default clip binds, which stops at the character.

A mesh the rig does not carry at all is judged differently. A handful hang
straight off the model root with no bone above them, so nothing takes them along
and they are placed by their own curves or not at all; a clip that binds one
only to hold it still says nothing about it, and those go by which clips drive
them instead. What separates Yoshimi's amplifier from a rifle parked in the air
beside the character is that set dressing is modelled standing on the floor, so
a prop resting on `y = 0` stays and one floating clear of it does not. This
branch used to catch most weapons, until the rigid binds below were read
properly; now that the rig carries them, almost nothing reaches it. (The halo is
left out of all of this; it gets hung off the head bone instead, above.) 19 of
the 283 models have something to hide, 24 meshes between them, and all but three
of those props come back for some clip.

**Meshes and the skeleton.** Vertices are left in mesh space, because Unity's
`m_BindPose` matrices are exactly the inverse bind matrices glTF wants: the
exporter mirrors the Transform hierarchy into glTF nodes, emits one skin per
skinned renderer, and lets the viewer do the skinning. Coordinates leave Unity's
left-handed space by mirroring X, which also means reversing triangle winding,
negating `y`/`z` of every quaternion, and conjugating matrices as `FLIP @ M @ FLIP`.
`_MainTex` is embedded as PNG; materials without one fall back to `_Tint`.

A rigidly bound mesh — every vertex on one bone, at full weight — is the case
to watch. Unity drops the BlendWeight channel from those meshes entirely and
ships only BlendIndices, so `MeshHandler.m_BoneWeights` comes back empty while
`m_BoneIndices` is full. Weapons and hand props are built this way, and reading
the missing channel as "not skinned" strands them wherever the bind pose left
them while the bones that should carry them animate on without them. The
exporter synthesises the implied weight of 1.0 instead.

**Transparency.** An alpha channel is not always an opacity. `MX/C-General/Layer4`,
the shader most bodies are painted with, keeps a layer selector in the alpha of
`_MainTex` — Kayoko (New Year)'s body texture is alpha 0 from corner to corner —
and `MX/C-Weapon` and the halo shader each keep something of their own there.
Read as transparency, those erase the character. So the exporter asks the shader
instead: the alpha is an opacity only where the first pass actually blends on it,
source factor SrcAlpha over OneMinusSrcAlpha. BA's shaders mostly write
`Blend [_SrcBlend] [_DstBlend]`, which serializes as 0/0 in the pass, so the
material's own `_SrcBlend`/`_DstBlend`/`_ZWrite` floats are the ground truth
there. A blending pass that still writes depth — the eyes and mouth, drawn over
the face — becomes glTF's `MASK`, which is the closest it has; `_AlphaClip` asks
for a cutout outright. Everything else is `OPAQUE`.

**Bundles outside the character's own set.** Characters are not self-contained:
a material, a `_MainTex`, or the atlas the mouth samples often lives elsewhere —
another character's bundles, the shared shader set, the preload group — and
UnityPy can only follow a pointer into a file it has been handed. Bundles name
their dependencies by serialized file rather than by bundle, so the exporter
reads the node table out of the header of every bundle shipped (a few KiB each;
26k bundles in about five seconds) to learn which bundle holds which file, and
opens one the moment a pointer needs it. The index is built once per process and
only if something actually reaches outside. Those bundles are loaded as
dependencies, so borrowing another character's texture does not also drag in
their body.

**Faces.** A character's own face texture has eyes but no mouth: the mouth is a
quad sharing the eye submesh whose UVs sit in a blank corner, which the toon
shader redirects into one tile of an expression atlas. Most characters share
`Character_Mouth`, a 1024x1024 grid of 64 expressions out of the preload set; a
few carry an atlas of their own, and not always on the same grid. The material's
`_MouthTileTex` names it and the resolution above reaches it, wherever it lives;
the exporter crops out the tiles it needs and gives the mouth quad its own
primitive and material. Without that the mouth is an opaque white patch. Which
tile the material is saved with is `uv * scale + offset` read back, and neither
term is tidy: an offset past 1 counts the tile off from a second copy of the
atlas, which the sampler wraps away — Ui's 1.625 is column 5, not column 13 —
and a negative scale mirrors the axis, which puts the offset on the tile's far
edge and the tile itself one cell back. Read literally, either one lands outside
the grid or on the neighbouring mouth. Some characters hang their eyes off a
second renderer, which leaves the mouth as a whole submesh rather than a corner
of the eye submesh; both shapes are found by the UV window that maps onto the
tile.

**Expressions.** The mouth is not a curve but an event track: each clip carries
Unity `AnimationEvent`s calling `SetMouthTile(row * 100 + col)` at the times the
expression should change, with the row counted from the bottom of the atlas
(Unity's UV origin), or `SetMouthTileToDefault()` for whichever tile the
material itself is saved with. A quarter of the clips change the mouth while
they play. glTF cannot animate a UV offset, so the exporter crops every tile a
character's clips ask for, gives each one its own copy of the mouth quad, and
switches between them with morph weights: each copy carries a single morph
target that folds it to a point, so a clip shows an expression by holding that
copy's weight at 0 and every other copy's at 1. The keys are `STEP`
interpolated, so the switch is exact rather than a fade, and the copies keep
their skinning — some characters rig the mouth partly to a `bone_mouth` of its
own, which a plain unskinned quad would lose. A model typically needs 4 to 16
copies of a 25-vertex quad, which costs a few tens of KiB.

**Spare faces.** An expression a character only pulls for a moment — Kasumi's
star-struck eyes, Aoba's blank stare, Neru's joke glasses and moustache — is not
a texture swap but a mesh of its own, sitting in the same place as the everyday
face and shipped switched on beside it. The game hides all but one at load; a
straight export leaves them stacked, which reads as two sets of eyes through one
another. Twenty-two of the bundles have more than one face, and what the mesh is
called is no guide to which is which, so they are found by material: a face
paints itself with the character's `_Face` material and nothing else of her,
whereas the body showing through it brings its own skin and hair along. Of those,
the everyday one is the one carrying the `_EyeMouth` material, since the mouth the
clips lip-sync belongs to the face the character talks with; a face kept for a
single line has its mouth painted on. Each face gets the mouth quad's treatment —
one morph target folding it to a point — and every face but the one being worn is
held at weight 1.

**Switching faces.** A clip swaps faces in one of two ways. It either animates
the GameObject's active flag, a generic binding with `attribute` 2086281974 —
`crc32("m_IsActive")` — which names its target by path like any other binding and
so is never in doubt, or it fires `AniEvt_EnableChildRenderer(i)` /
`AniEvt_DisableChildRenderer(i)`, where `i` is a place in a list the game builds
at load time and the prefab does not record. Reading that number as an index into
the model root's children is right for most characters and wrong for a few, and
nothing in the bundles settles it: the build is il2cpp, and the prefab roots carry
only a Transform and an Animator. So the numbers are checked against the character
herself. Every face ships switched on and the clips switch the spare ones off, so
the face worn at a given moment is whichever one a clip leaves on by itself; if
reading the idle clip that way puts her in her everyday face, the events are
believed and the clips swap faces as they should, and if it does not, they are
indexing something invisible here and are dropped, leaving her in her everyday
face throughout. Three characters — Kasumi, Neru (School Uniform) and Hasumi
(Swimsuit) — fall on the second side today; the rest are read as written.

**Animations.** The clips are Mecanim, not legacy, so there are no
`m_RotationCurves` to read — every float curve is packed into
`m_MuscleClip.m_Clip` as three concatenated arrays (sparsely keyed *streamed*,
evenly sampled *dense*, and *constant*), and `m_ClipBindingConstant` says which
transform property each run of curves belongs to. `export_models.py` decodes the
streamed byte stream itself, since UnityPy has no helper for it, and resolves the
binding path hashes to bones through the Avatar's `m_TOS` table. Curves become
glTF samplers at their native key times.

## Known gaps

- Animation keys are interpolated linearly. Unity evaluates the same curves as
  Hermite splines, so fast motion is very slightly flatter than in-game.
- Channels that hold still at the node's rest transform are dropped — three.js
  restores unbound nodes to their rest value, and keeping them roughly tripled
  file size. A viewer that does not restore rest state would need them back.
- Clip names keep the game's own naming (`Formation_Idle`, `Exs`, `Vital_Death`);
  only the character prefix is stripped.
- Expressions follow the clip's own event track. During voiced lines the game
  overrides it with a separate lipsync layer driven by the voice data, which is
  not in the model bundles, so what is exported is what you see in unvoiced
  contexts such as the lobby and in battle.
- Where a character's face events are dropped, she keeps her everyday face for
  every clip: Kasumi's eyes never turn to stars, Neru never puts the glasses on.
  Reading the index would need the renderer list the game builds at load time,
  which is in `GameAssembly.dll` rather than in the bundles.
- Apart from the mouth atlas, only `_MainTex` is used. The game's toon shader
  also relies on mask and specular textures, so shading is flat;
  `data-shading="unlit"` in the viewer is the closest cheap approximation.
- The halo is attached rigidly, so it takes the head's rotation as well as its
  position. The game's walking modes — the cafe and the world raid map — run
  the halo through a follower that damps both, so it lags the head a little
  there; a follower is a per-frame simulation, which a glTF clip cannot hold.
- Outline (`OL_`) meshes are dropped; the gadget's own `outline` option can stand
  in for them.
- Which prop belongs in which clip is read off the clips' bindings and, for the
  props the rig does not carry, off whether they rest on the floor. Both are
  inferences, not statements the files make: a prop the artist parked at ground
  level is kept whatever the clip does with it.
- Props the game spawns on rigs of their own go with the effects: Shiroko
  Terror's pufferfish, Cherino's capybara, Utaha's robots. They stand beside the
  character rather than being part of it, and their clips leave with them.
- Compressed meshes hand back a junk value in the bone-weight slot Unity implies
  rather than stores; the exporter refills it with the leftover weight.
