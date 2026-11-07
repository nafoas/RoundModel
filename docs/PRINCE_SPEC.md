# Prince — what he looks like

Source: the owner, in conversation. Do not invent details beyond this; add to
it only from the owner or from the reference photos (and say which photo).

## Overall
- A small, white, very fluffy rabbit. "A very good round boy." "The best tiny
  little loaf around."
- **Very round.** The body is the dominant shape; everything else is small
  relative to it.
- **Barely a neck.** The head flows into the body. Because of this, when he
  looks at you he faces you with his whole front, head-on, eyes fully fixed.
  Very curious expression.
- **Tiny ears.** Small relative to the head.
- **Short legs; feet barely stick out under his body.** He has no real stride;
  his feet go quickly underneath him ("peetpeetpeet"). In a resting pose the
  feet should be only slightly visible below/ahead of the body.
- Color: white (texture is a later phase).

## Owner's framing (important)
- The owner provided 30-40 photos covering every angle, close-ups, from above
  and below, and of specific body parts.
- **This is not a hard shape.** He is very round with tiny ears and barely
  visible feet. Do not treat the task as too hard or excuse shortcuts by its
  difficulty; the difficulty is only in getting proportions exactly right, which
  the numeric pipeline handles.
- He means a great deal to the owner. "Close enough" is not acceptable. The
  numbers define close enough.

## The anchor photo
- One photo is Prince from the front, dead on, eyes on, staring as neutrally
  and curiously as possible. This is "him at his most him."
- Filename: `data/photos/anchor_front.webp` (added at the owner's request,
  2026-11-07). Record it in `config/thresholds.json` as `anchor_view`.
- Note: this copy came through chat (WebP, background already removed) and may
  be recompressed/downscaled. If the owner has the full-resolution original,
  prefer it and replace this file (owner's call).
- Image is 1098×1433, RGB, no alpha. The removed background is **pure white
  (255,255,255)**, and Prince is **not**: his fur measures roughly 185-228 on
  the face and is darker/bluer in the shaded chest and sides. Only ~3% of pixels
  in his body region hit pure white, vs ~99.9% of background. So the boundary is
  clean and a measurement mask can be made reliably by separating pure white
  from everything else (owner spotted this; measured 2026-11-07). Whiskers are
  ignored (weight 0) and wisps excluded when measuring the body; see STRAND_PLAN.
- Rule: the model, rendered from that camera, must match this photo most
  closely of all views. Its scoring weight is the highest.
- What "keep it immutable / don't distort it" means: it is the **ground truth
  everything is checked against**, NOT the model itself. A previous session
  misread this as "trace the front silhouette and cut it out". Never do that.
  The other photos supply depth, back curve, ear angle, etc.

## Modeling implications (how the spec maps to parameters)
_Early sketch; to be reworked to the parts above (head, undercarriage, ears,
peets) before any model code is trusted._
- Body: one large flattened ellipsoid ("loaf"), resting on the ground plane.
- Head: an ellipsoid smoothly blended into the body with a large blend radius
  (that's the "barely a neck").
- Ears: two small rotated ellipsoids, symmetric.
- Feet: four small ellipsoids, mostly hidden under the body.
- Tail: a small sphere at the back.
- Fur: modeled as part of the overall silhouette (the fluffy outline *is* what
  we match). Real fur strands are a late, optional phase.

## Per-photo notes
_For each photo the owner adds to `data/photos/`: filename, rough viewing
angle, pose (loaf / sitting / other), anything notable. Say which photos you
used as references for each decision._

## Anchor photo — observations (owner shared it in chat, 2026-11-05, session 2)
File: `data/photos/anchor_front.webp`. Background already removed.
Front view, camera at roughly his eye/nose height, very slightly above.
- **Silhouette:** one continuous rounded mass. Head and body read as a single
  shape; the widest point is the lower body (around the cheeks/chest and below),
  which is wider than the top of the head. Slightly pear/bell shaped from the front.
- **Head–body join:** no visible neck. There is a soft horizontal fold under the
  chin/mouth where the chest fur meets the face; that's the only hint of a join.
- **Ears:** very short, wide, rounded tips, set high and fairly far apart, leaning
  slightly outward. Barely taller than the fur on top of the head.
- **Eyes:** dark, glossy, with visible highlights; set wide on the sides of the
  head, slightly forward. A thin dark rim ("eyeliner") and dark lashes.
- **Nose/mouth:** pink nose with a Y-shaped split into the mouth; small and
  centered, about midway down the front silhouette.
- **Feet:** two front paws barely visible at the bottom, close together under
  the chest, with a few small dark specks on them.
- **Fur:** dense, white, soft; the outline is fuzzy, with sparse longer guard
  hairs sticking out, especially at the sides. Faint gray/blue shading on the
  chest and lower body (lighting/shadow, not color). Long thin whiskers from
  the cheeks, extending well past the silhouette.
- **Goal set by owner:** from this exact camera position, a render should be
  hard to tell apart from this photo. Owner's view: the shape is subtle but not
  complex; **fur is ~80% of the work.**

## Parts — owner's decomposition (2026-11-07)
Owner's direction: split Prince into his constituent parts so the outline is
never accidentally distorted. A previous attempt misunderstood his shape.

1. **Head** — smoother, shorter fur; slopes outward from the narrow top (between
   the ears) down to the cheeks. Eyes, nose, mouth live here. Ends at the soft
   fold under the chin.
2. **Undercarriage** — where a neck would be, he instead has a fluffy mass under
   the chin: chest and lower body, longer/coarser fur, bluish shading. It ends
   at the approved peets/underfluff line (`data/lines/peet_line.json`).
3. **Ears** — short, wide, rounded; set high and apart, leaning slightly out.
4. **Peets** — his two tiny front feet, close together under the undercarriage,
   small dark specks. The left peet sits higher in the photo and is lighter
   (cream); the right is a squarish, slightly lighter gray block.
5. **Fluff tufts** — e.g. the tuft hanging between the peets.
6. **Wisps** — long wispy hairs (full length) and the fluff under the peets.
7. **Whiskers** — their own class. See "Whisker & wisp layer" below and
   `docs/STRAND_PLAN.md`.

### Measured from the anchor photo (whiskers/wisps removed)
Body outline width by image row (photo is 1098×1433 px):
| row | width px | note |
|---|---|---|
| 241 | ~326 | ears / top of head |
| 401 | 432 | forehead, eye level begins |
| 601 | 734 | cheeks widening |
| 801-841 | **~852 (max)** | mouth/chin level: cheeks over top of undercarriage |
| 961 | 792 | undercarriage |
| 1081 | 710 | lower undercarriage |
| 1161-1201 | 525-573 | paws |
- The outline is **one continuous curve with no notch** at the head/undercarriage
  join. The split shows only *inside* the silhouette: the chin fold and the
  change in fur texture.
- Fur texture (mean local pixel std): head ~1.5-1.8, undercarriage ~3-5.
  The undercarriage fur is measurably fluffier.
- Center line drifts slightly (x ≈ 523-567): small asymmetry in pose or camera.
  Don't force perfect symmetry on the anchor without checking other photos.

### Rule that follows from this
The parts must **add up to exactly the measured outline**. Fitting happens on
the whole outline (minus whiskers/wisps); the head/undercarriage split governs
the *fur* (length, fluffiness, shading) and the interior fold, never a change
to the outline.

## Whisker & wisp layer (owner's requirement)
- Whiskers and the thin wispy guard hairs past the fur edge must appear **as
  they are, completely unchanged**, added meticulously as a final layer.
- They are **excluded** from the body outline used for fitting, so they can't
  distort it.
- First-pass separation (2026-11-07, scratch only, not saved to `data/`):
  everything not pure white = Prince; a morphological opening (disk radius 9
  px) keeps the body; the thin structures left over (~19k px of ~684k) are the
  whiskers/wisps.
  **CORRECTION: this was wrongly reported as a clean split.** It was judged from
  a downscaled overview. The owner caught the failures; zoomed full-res crops
  confirmed them:
  - **Fluff under and between the feet** (counts as wispy hair, per owner) was
    left in the body or missed entirely (palest fluff fell below the
    "not white" cutoff of < 250).
  - **Bases of the wispy hairs** at the sides were absorbed into the body:
    the opening treats anything thicker than ~18 px as body, and clustered
    wisp roots are that thick. Only wisp tips were separated.
  - Whiskers lying over the fur inside the outline are also not captured.
  Conclusion: simple thresholding + morphology can't decide where the coat
  ends and the wisps begin. Two more automatic versions also failed (they
  labelled the tufts under the undercarriage as body). The method is now
  part-by-part and strand-by-strand: `docs/STRAND_PLAN.md`.
- **Owner's definition:** fluff under the feet and the full length of wispy
  hairs, *including their bases*, belong to the wisp layer, not the body.
