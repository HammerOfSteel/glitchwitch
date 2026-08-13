# Character Art Generation Prompts (Meshy AI)

Companion to `docs/character-inventory.md`. Generate a **3-view reference sheet**
(front / side / back) per character with a text-to-image tool of your choice (the
style anchor below is model-agnostic — tested phrasing works well with Midjourney,
SDXL-family models, and DALL-E-family models), then feed those views into **Meshy AI's
Image-to-3D** (multi-image mode: front + back + (optionally) side) to generate the
rigged base mesh. T-pose is called out per character where it matters for rigging.

## Why a style anchor

Every character must read as being from the *same game*. The style anchor is a fixed
block of text you paste into **every** prompt, unchanged, so the generative model
locks onto one consistent look across ~30+ characters generated over time (possibly in
different sessions/days). Per-character text only ever *adds* detail — it never
contradicts the anchor.

The anchor is written from `docs/design-bible.md`'s art direction: toy-box/diorama
look, Animal Crossing-adjacent proportions, English/Welsh hedge-country cottagecore
setting, warm muted earth-tone palette, no combat gear.

---

## The style anchor (paste verbatim into every prompt)

```
cozy cottagecore RPG character concept art, chibi-adjacent proportions (slightly
oversized head, short soft limbs, huggable rounded silhouette, Animal-Crossing-like
warmth), clean thick dark-brown ink outlines, flat cel-shaded toon lighting with soft
2-3 step shading and a gentle warm rim light, painterly-but-simple texture (no photoreal
skin/fabric detail), muted warm earth-tone palette (moss green, cream, honey, clay,
stone grey, cardigan rust, soft wood brown), English hedge-country village setting,
storybook illustration quality, single character centered on a plain flat neutral
light-grey background, orthographic character reference sheet framing, consistent
scale and proportions, no shadows cast on the ground, no props unless specified, no
other characters, no text, no watermark, no signature
```

**Negative prompt (if your tool supports one):**
```
photorealistic, hyperrealistic skin texture, dark/gritty/horror tone, combat armor,
weapons, blood, modern technology (smartphones, sneakers, jeans), extra limbs, extra
heads, cropped body, cropped face, motion blur, background scenery, multiple
characters, text, watermark, signature, logo
```

**Per-view suffixes** (append exactly one to the style anchor + character description):

- Front view: `, front view, facing camera directly, arms and legs fully visible, T-pose (arms straight out to sides, palms down) for rigging reference`
- Side view: `, full side profile view (facing screen-left), T-pose (arm straight forward, palm down) for rigging reference`
- Back view: `, back view, facing directly away from camera, T-pose (arms straight out to sides, palms down) for rigging reference`

For **quadruped** and **bird** archetypes, replace the T-pose clause in each suffix with:
`, natural standing/perched pose, neutral relaxed limb position for rigging reference`
(quadrupeds/birds don't T-pose — Meshy's multi-image mode works fine from a neutral
stance shown from 3 angles instead).

For the **small-creature** archetype (The Kindlies), replace the T-pose clause with:
`, simple frontal presentation pose, arms slightly out from body, for rigging reference`.

---

## How to use this file

1. Copy the style anchor block.
2. Copy one character's description block below.
3. Append one of the three per-view suffixes.
4. Generate. Repeat for the other 2 views, same character, same seed if your tool
   supports seed-locking (keeps proportions/colors consistent across the 3 views).
5. Feed the resulting front/back(/side) images into Meshy AI's Image-to-3D.
6. Cross-check the result against the rig contract for that archetype
   (`tools/assetgen/rig_contract.py`) before committing to a final import.

---

## 1. Player

### Wren
```
[style anchor], a young apprentice hearth-witch in her early twenties, slim build,
average height, hair in a single loose braid, wearing a soft rounded felt witch hat
(not tall or pointed — cozy, not villainous), a simple cream work-dress under a
patched moss-green apron with pockets, sensible worn brown boots, a small satchel at
her hip, warm friendly expression, slightly windswept and rumpled like she just
arrived somewhere new
```

## 2. Named cast

### Sigrid Barm (baker)
```
[style anchor], a warm sturdy woman in her late fifties, stout build, strong
flour-dusted forearms, hair wrapped in a practical honey-colored scarf, wearing a
cream apron over a simple wood-brown dress, rolled sleeves, kind squint-lined eyes,
faint flour dust on her hands and apron
```

### Ansel Rowe (postman)
```
[style anchor], a wiry upright man in his forties, weather-creased friendly face,
wearing a worn clay-brown postal cap with a small tarnished brass badge, a canvas
satchel bag slung across his chest, sturdy boots worn pale at the toe, simple
practical work clothes in muted rust and stone tones
```

### Maud Tressel (elder)
```
[style anchor], a small slightly stooped elderly woman in her seventies, silver hair
in a neat coil, wearing a knitted shawl with a faded floral rose-pink trim over a
plain stone-grey dress, small round reading glasses on a chain, soft house slippers,
a gentle wistful expression
```

### Juniper Vale (teen)
```
[style anchor], a gangly restless teenager, mid-teens, wearing an oversized
hand-me-down moss-green cardigan with sleeves past the wrists, an old-fashioned
crystal-radio headset resting around the neck (vintage dials and a small speaker cup,
not modern tech), a canvas bag covered in small hand-sewn badges, hair a little
messy, an eager curious expression
```

### Torben Ask (forester)
```
[style anchor], a tall broad quiet man in his thirties or forties, short beard,
wearing layered flannel-weave earth-brown clothing, a canvas satchel and a
resting-at-rest hand axe hung from a belt loop (a tool, held loosely, never raised or
threatening), moss-stained sturdy boots, a calm weathered expression
```

### Greta Furrow (farmer)
```
[style anchor], a sturdy sun-weathered woman in her forties, wearing a wide-brimmed
straw hat, overalls in faded honey-brown over a simple linen shirt with rolled
sleeves, a seed-pouch belt at the waist, strong capable hands, a squinting
sun-warmed smile
```

### Ines Jarvi (shopkeep)
```
[style anchor], a neat precise woman in her thirties, wearing small round
spectacles, hair pinned up with a pencil tucked through it, an apron with many
small labeled pockets each holding a tiny jar, a soft rust-colored cardigan over a
ceramic-blue-grey blouse, an organized attentive expression
```

### Fenn Solder (tinkerer)
```
[style anchor], a lean fidgety young adult in their twenties or thirties, wearing
brass-rimmed goggles pushed up on the forehead, a patched jacket with mismatched
buttons, a tool belt holding small gears/wire/solder-tools (no weapons), metal-grey
and rust tones with one small glitch-cyan accent (a glowing trinket or patch), an
excitable optimistic expression
```

### Hollis Bram (warden)
```
[style anchor], a tall formal man in his fifties with a worn-but-dignified bearing,
wearing a long stone-grey coat with a small brass warden's pin at the collar, holding
a closed ledger/clipboard prop against the chest, steady composed expression, neat
grey-streaked hair
```

### Odell Rime (teacher)
```
[style anchor], a tidy patient adult in their thirties, wearing a chalk-dusted
cream-and-moss cardigan, small spectacles, hair neatly tied back, holding or wearing
a small satchel of books, a warm encouraging expression
```

### Eamon Brook (fisher)
```
[style anchor], a weathered calm man in his forties or fifties, wearing a
water-blue-grey oilskin coat, wide clay-brown waders, a small knit cap, a woven
fishing creel slung at the hip (no visible hook or blade), a quiet half-smile
```

### Tansy Mothwood (hedge-witch)
```
[style anchor], a spry sharp-eyed elderly woman in her sixties or seventies,
wild silver hair, wearing a deliberately mismatched patchwork shawl in moss and
honey tones with one tiny void-plum-purple patch, small round glasses, carrying a
woven herb basket, a knowing mischievous smile
```

### Pip (kid)
```
[style anchor], a small quick child around eight years old, chibi child
proportions, scraped knees, oversized hand-me-down boots, a gap-toothed grin,
slightly muddy cream-and-clay play clothes, an energetic mischievous pose feel
```

### Nettle (kid)
```
[style anchor], a small watchful child around ten years old, chibi child
proportions, hair in two braids with mismatched ribbons, a bulging collector's
pocket bag at the hip, light freckles, moss-and-honey play clothes, a curious
observant expression
```

### Sal A. Manda (traveling DJ)
```
[style anchor], a theatrical adult in their thirties or forties, wearing a
patchwork travel coat covered in small salamander-shaped pins, a long scarf that's
a bit too long trailing past the knees, carrying a portable crystal-radio case,
a wide friendly showman's grin, rust-and-honey tones with one small
glitch-magenta accent (a glowing dial or pin)
```

## 3. Companion animals

### Clack (magpie)
```
[style anchor], a magpie with accurate glossy black-and-white plumage, sharp
alert eyes, perched in a natural alert stance with head level, [use bird per-view
suffix]
```

### Click (magpie)
```
[style anchor], a magpie with accurate glossy black-and-white plumage matching
Clack's coloring, but with head cocked slightly to one side and one asymmetric tail
feather, so the pair is recognizably two individuals, [use bird per-view suffix]
```

### Parity (cat)
```
[style anchor], a short-haired black cat with one white front paw ("sock"),
calm dignified sitting posture, round attentive eyes, [use quadruped per-view
suffix]
```

### Cache (cat)
```
[style anchor], a long-haired orange tabby cat, slightly round heavy build, one
faintly notched ear, a sleepy contented posture, [use quadruped per-view suffix]
```

## 4. Small creatures

### The Kindlies (base design)
```
[style anchor], a palm-sized round pantry sprite, roughly humanoid-blob shaped
with no visible legs (floats/hovers just above the ground), short stubby arms,
large expressive round eyes, a soft doughy bread-roll-like body texture, holding
one small wooden spoon prop, a fussy tidy silhouette, cream-and-honey coloring
with one small pastel accent color, [use small-creature per-view suffix]
```
> Generate this base design once, then re-skin the same silhouette with a different
> single pastel accent color per palette variant (no new geometry needed — recolors
> only) for additional Kindlies individuals.

## 5. Proposed background/support NPCs

### Background Villager — Elder A
```
[style anchor], a stooped elderly background villager, using a simple wood cane,
wearing a flat cap, stone-grey and cream clothing, a neutral pleasant ambient
expression (not a specific personality — a crowd/filler character)
```

### Background Villager — Adult B
```
[style anchor], a mid-build adult background villager, wearing a clay-brown apron,
carrying a woven basket on one hip, moss-green underlayer, a neutral pleasant
ambient expression (crowd/filler character)
```

### Background Villager — Adult C
```
[style anchor], a lean adult background villager, wearing a simple wood-brown
waistcoat with a small pocket-watch chain, honey-toned shirt, a neutral pleasant
ambient expression (crowd/filler character)
```

### Background Villager — Teen D
```
[style anchor], a teenage background villager, carrying a satchel of books,
knee-patched trousers, leaf-green and cream clothing, a neutral pleasant ambient
expression (crowd/filler character)
```

### Corwin Dale (relief postman)
```
[style anchor], a younger eager adult in their twenties, wearing an
ill-fitting borrowed postal cap slightly too big, clay-brown and metal-grey
postal clothing, an earnest slightly nervous smile
```

### Bramwell Auk (village doctor/herbalist)
```
[style anchor], a tall calm adult, wearing small half-moon glasses, carrying a
satchel of small herb jars, ceramic-blue-grey and moss-green clothing, a
reassuring gentle expression
```

### Rosalind Byre (innkeeper)
```
[style anchor], a warm round-faced adult, a ring of small keys on a ribbon at
the belt, honey-and-cream clothing with a rust-colored apron, a welcoming
hospitable smile
```

## 6. Glitch fauna (anomaly creatures — non-combat)

> **Important:** generate the *base creature* first with a normal, non-glitched
> reference sheet (a plain blackbird, a plain hare, a plain hen, a plain fox, a
> plain stray cat), matching real-world proportions for that animal blended with
> the style anchor. Apply the anomaly visual verb as a **material/shader effect in
> Godot** (ghost trail, wireframe tear, magenta-checker patches, duplicate mesh
> instance), not as baked-in generated art — this keeps one clean base model reusable
> for both its "normal" and "glitched" states, matching the design-bible.md rule that
> anomalies are diegetic effects, not separate monster designs.

### The Looping Blackbird (base: ordinary blackbird)
```
[style anchor], an ordinary garden blackbird, glossy black plumage, small yellow
beak, natural perched-and-about-to-fly pose, [use bird per-view suffix]
```

### The Lagging Hare (base: ordinary hedge hare)
```
[style anchor], an ordinary brown hedge hare, long alert ears, natural
crouched-ready-to-hop pose, [use quadruped per-view suffix]
```

### The Duplicated Hen (base: farm hen)
```
[style anchor], an ordinary speckled brown farm hen, small red comb, natural
standing pose, [use quadruped per-view suffix]
```

### The Seamed Fox (base: village fox)
```
[style anchor], an ordinary red village fox, bushy white-tipped tail, alert
sitting pose, [use quadruped per-view suffix]
```

### The Missing-Textured Cat (base: unnamed stray cat)
```
[style anchor], an ordinary tabby stray cat (visually distinct from Parity and
Cache — lankier, scruffier fur), a wary watchful posture, [use quadruped per-view
suffix]
```

### The Echo Moth (flagged — do not generate until design approves the 6th glitch verb)
```
[style anchor], an ordinary pale garden moth, soft dusty wing pattern, wings
spread flat as if pinned for a reference sheet, viewed from directly above /
front / back, natural resting pose
```

---

## Notes for the Meshy AI import pass

- Keep a **fixed seed** per character across its 2–3 view generations where the tool
  allows it — this is the single biggest lever for getting views Meshy can actually
  reconcile into one coherent mesh.
- If Meshy's reconstruction drifts on proportions between views, regenerate the
  *side* view only (front and back matter most for Meshy's mesh topology; side mostly
  informs depth) rather than redoing all three.
- After import, cross-check triangle count against `docs/design-bible.md`'s budget
  (characters ≤ 4,000 tris) before committing the asset — Meshy exports are often
  denser than that and need a decimation pass.
- Update the corresponding row's `Status` column in `docs/asset-inventory.md` from
  `planned` to `sourced (Meshy)` once a character's final GLB lands in
  `assets/thirdparty/` (matching the existing Wren-placeholder pattern), and swap the
  in-engine loader over per that file's placeholder-swap convention.
