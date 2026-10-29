# Tasks: Prince rebuilt from the master's front (owner, October 2026)

Agreed with the owner after the normal-map work (tasks/02). The old model
is abandoned: "The model just isn't right at all. It doesn't look like him
at all and I see no redeeming qualities in using it." Re-read CLAUDE.md,
docs/INTENTS.md, docs/PHOTOS.md, docs/MEASURING.md and this file at every
milestone.

## The method (owner)

Turn the master's normal map directly into a model and take that as the
immutable front-facing model, to fill in from, everything else made to
conform to the master, never the other way round.

- Blender add-ons that turn a normal map into a model (e.g. DeepBump) do
  normal integration (map -> height field -> displaced sheet), the same
  thing tools/master_shell.integrate already does; installing one means
  fetching outside code, which this environment blocked before (DSINE). So
  the integration in this repo is used (owner may ask to try a plugin).
- The old model is not used for anything: not for shape, not for scale.

## Steps

- [ ] 1. (built; shown to the owner, checkpoints/cp6/front.jpg, front_sheet.png; regenerate: python tools/master_front_mesh.py work/m/front) The front, from the master alone: his front surface from the
  master's normal map (checkpoints/cp5/maps/master_front_standing), over
  his whole outline, full resolution, as a mesh (tools/master_front_mesh.py).
  Immutable from here on. Its one free number, his distance (size), from
  the master camera: his nose tip at the master camera's depth for it
  (until the owner gives his real width or length). Shown to the owner on
  its own, from the front and from the side.
- [ ] 2. (first try stopped, not used: the other photos cut most of the master's face away (their cameras, solved against the old model, don't line up with the new front; and the front wasn't protected from them), the hidden parts came out faceted, and the block was too short (flat back). Proposed to the owner: re-solve the other cameras against the new front, never cut what the master sees, longer block, shape the hidden parts with normals. Waiting for the owner.) Fill in the rest from the other solved photos: their outlines
  carve what the master can't see (sides, top, back, underneath,
  haunches), their normals shape it; the fill meets the front's edge
  smoothly and never moves the front. Ears from the photos that show them.
- [ ] 3. Checked after each step: master first, then the profiles and the
  top-down; then the close-ups.

## Known risks (said up front)

- The master can't show depth jumps inside his outline (how far his chin
  stands off his chest, how deep his body goes behind his cheeks): the
  profiles decide those, and may show the front's overall depth scale needs
  changing (one number, not its shape).
- The other photos' cameras were solved against the old model: still in the
  same world frame as the master, but some may need re-solving against the
  new shape.

## Standing rule for this stage (owner)

If a step comes out looking wrong, or a number is far outside what I
expected, I stop and tell the owner plainly ("this isn't going well")
before doing anything else. No pushing through, no new fix written first.
