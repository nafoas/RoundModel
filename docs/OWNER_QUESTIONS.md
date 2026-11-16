# Questions for the owner's bulk review

Things decided on intuition + earlier guidance while working on my own, to get
the owner's official opinion later. Each says what I did in the meantime.

1. **Half-pixel correction (batch 1).** I found the outline was stored half a
   pixel off (up-left) from how everything else counts pixels. The sheets you
   approved for batch 1 showed the line half a pixel up-left of where it really
   was. Fixed project-wide (test added); batch 1 sheets regenerated. *Meantime:*
   batch 1 stays approved; please glance at the regenerated sheets
   (`docs/images/batch1_outline_*.png`) to confirm.

2. **Notch where each peet meets his body side** (T039-T041 his left, T059-T060
   his right). In the outline these show as a small inward hook / S-shape: the
   line dips into the real notch (where the approved peet line starts) and swings
   back out around the peet. *Meantime:* kept, since it's a real feature and each
   peet gets its own precise step later. Picture: `docs/images/batch3_outline_2.png`
   (T059-T060) and `batch2_outline_2.png` (T039-T040).
3. **Tuft spike tips** (T047-T052). The outline follows the tuft's big scallops;
   its thin hanging spike tips fall just outside, like fringe elsewhere. *Meantime:*
   per the guide ("tufts: FLUFF, tips included"), the tips will be included when
   the tuft gets its own FLUFF step.

4. **[ANSWERED 2026-11-08: intermediate fur goes first; the peets and ears are split off later along the lines drawn earlier.]** **Intermediate fur: its own step, and when?** You said the intermediate fur
   between his body and the wisps gets its own colour. *Meantime:* I've made it
   its own class and would give it its own step right after the body outline
   (before the ears), since it borders every part. Its outer edge is where the
   wisps begin. Please confirm the order.
5. **The fringe guide changed.** Golden-tile guide #3 said feathery fringe is
   the body's soft edge; your newer word (intermediate fur is its own colour)
   supersedes it. Recorded as guide #3b in METHOD.md.
6. **Small notches between fur clumps** at the base of the fringe (3-5 px deep,
   e.g. T019-T031, T066-T081): the smooth body line bridges them rather than
   dipping into each one. *Meantime:* bridged, for a gentle edge.
7. **[ANSWERED 2026-11-08: "the bulge is also part of his brow ridge" → read as: it's him, keep it as body. Correct me if I misread.]** **Dense dark clump at the base of his fringe** (T019-T020, his left cheek,
   image right): the body line swings out around it, treating it as body because
   it's as dense as body fur. *Meantime:* kept as body; if it's intermediate fur,
   the line should pass behind it.
8. **[ANSWERED 2026-11-08: "could maybe go in just a tiny bit" → density 0.18 → 0.21, about 1 px in on average.]** **Where the outer edge of the intermediate fur sits.** I tried three settings
   (tight / middle / loose) and chose the middle one: most short fringe spikes
   end right around it; long single hairs carry on past it (they're wisps or
   whiskers). Long straight strands (whiskers, long wisps) are removed before
   measuring, so where they fan out together they don't drag the edge out.
   *Meantime:* middle setting. Sheets: `docs/images/batch*_fur_*.png`.
9. **[ANSWERED 2026-11-08: ears and eye lashes need to be incredibly precise; done separately, eventually.]** **Ear halo.** Guide #7 said the ear's halo is the ear's soft edge; with the
   newer rule (fringe outside the body line = intermediate fur), the thin halo
   (2-3 px) is now in the intermediate fur band. *Meantime:* intermediate fur;
   when the ears get their own step, the halo can be reassigned to them.
10. **[ANSWERED 2026-11-08: same; lashes get their own separate precise step.]** **Lash bases.** At both eyes the band takes in the bases of the lashes; the
   lashes continue past it. *Meantime:* bases in the band, lashes beyond it
   handled as strands (wisp rule) later. Should lashes be their own class?
11. **[v1 ANSWERED 2026-11-08: top connections fine; lines must follow the peets' curvature. v2 proposed, see below.]** **Dividing the peets from the tuft** (needed before the peets can be split
   off). Below the approved peet line there are three parts: the cream peet
   (image left), the tuft and the gray peet (image right). I drew two proposed
   dividing lines (`docs/images/peet_dividers_proposed.png`, zoom
   `peet_dividers_zoom.png`; data `data/strands/peet_dividers.json`, PROPOSED).
   Colour tracing was pulled off by shadows (the tuft's shadow on the cream
   peet; the gray peet's own shadowed corner), so they're placed by shape:
   where each peet's rounded mass ends and the tuft's vertical hair begins,
   ending at the corner where the outline turns up into the tuft. *Meantime:*
   stopped here for your check, since the peets are sensitive (stance).
12. **[v2 ANSWERED 2026-11-08: gray fine; cream's connection to the purple line still cut off part of the peet → v3.]** **How far the peets bulge toward the tuft (v2).** That edge is in shadow and
   not directly visible, so v2 follows each peet's fitted roundness: the cream
   peet bulges up to 17 px past v1, the gray peet up to 8 px. Bottom corners kept
   from v1. *Meantime:* proposed; tell me if either bulges too much or too little.
13. **[v3 ANSWERED 2026-11-09: tuft fur covers part of the peet's edge but the peet extends under it; don't cut the peet off for the fur → v4.]** **Cream peet divider v3.** Junction with the purple line moved from x 433 to
   x 450 (above the widest point of the peet's side), shoulder rounded into the
   purple line, lower part unchanged. The photo shows no sharp edge there (the
   cream fades into the tuft's blue), so the exact spot is judgment. *Meantime:*
   proposed; zoom `docs/images/peet_dividers_zoom.png` (thin red = v2).
14. **[ANSWERED 2026-11-09: approved; owner moved on.]** **Cream peet divider v4** (whole peet under the tuft fur): widest at x 464.5,
   ends on the peet's visible rising side. *Meantime:* proposed.
15. **[ANSWERED 2026-11-09: 'the gray peet seems fine'.]** **Gray peet and the same rule.** You approved the gray line as is. By the
   same rule (parts continue under covering fur), the gray peet's left edge might
   also reach a little under the tuft. *Meantime:* left unchanged since you
   approved it; say if it should get the same treatment.
16. **[ANSWERED 2026-11-09: approved, 'it all seems good'.]** **Where the peet line meets the outline.** The approved peet line stopped
   short of the (later refined) body outline at both notches. Cream side: its own
   direction continued 9.8 px lands in the notch. Gray side: continuing straight
   would overshoot onto his body side, so it now turns down the gray peet's
   shadowed right side to the notch (a rounded top-right corner; inferred).
   *Meantime:* used for the split; picture `docs/images/parts_peets_zoom.png`
   (right panel).
17. **[ANSWERED 2026-11-09: go pixel by pixel like the eyes, every notch and kink and the base on the left; asymmetry is fine → v2.]** **Where each ear meets his head** (`docs/images/ear_bases_proposed.png`,
   zoom `ear_bases_zoom.png`). Ear on image right: a clear crease, followed;
   its inner end is where the dip between the ears starts rising, its outer end
   where the crease meets the ear's shaded outer side (y 308; the outline has a
   very slight kink higher up at y 254 that I did NOT use). Ear on image left:
   the crease is faint; the line runs from the ear's outer corner to the bottom
   of its step into the dip, so the small ledge belongs to the ear. The flat dip
   between them is the top of his head. *Meantime:* proposed; the two bases
   aren't symmetric (right one ~20 px lower outside), left as the photo shows.
18. **[ANSWERED 2026-11-09: both bases a bit lower, down to where the ear meets the flat part → v3; hook and mirrored base not objected to.]** **Ears v2 (pixel-precise).** (a) The little outward hook at the outer base of
   the ear on image left: I counted it as part of the ear (ears flare where
   they attach), so the base ends just below it. (b) That ear's base shows no
   crease in the photo, so it uses the other ear's measured crease shape,
   mirrored. (c) The ear on image right's base now ends on a real notch at
   (715.8, 300.2), 7.7 px higher than v1. *Meantime:* proposed; pixel views
   `docs/images/ear_left_pixels.png`, `ear_right_pixels.png`.
19. **[ANSWERED 2026-11-09: too far; ~3 px. Also the base on the left side of the orange ear wasn't covered → v4.]** **Ears v3: how far down.** You said "a tiny bit"; measured, the flat part
   starts ~12 px below the v2 lines (12-16 px on the ear on image right, ~14
   on the other), so both are 12 px lower in the middle, easing to no change at
   the inner corners. *Meantime:* proposed; if 12 px is more than you meant, I
   can go halfway. Thin red = v2 in `docs/images/ear_*_pixels.png`.
20. **[ANSWERED 2026-11-11: green ear fine; orange ear's right side down a tiny bit more, left side ~3 px more → v5.]** **Ears v4.** Both bases 3 px below v2 (easing to 0 at the inner corners).
   The orange ear's base flares outward below its hook (the outline runs
   straight from the hook to (351.5, 311.8), then curves as his head's side);
   the line now sweeps down that flare and ends where it becomes his head.
   *Meantime:* proposed. Thin red = v2 in `docs/images/ear_*_pixels.png`.
21. **[ANSWERED 2026-11-11: approved.]** **Orange ear base v5.** 3 px below v4 along its whole length; at the inner
   notch the drop eases in over 14 px (a 6 px ease kinked), so the right side is
   1.7 px lower at x 505 and 3 px lower from x 500 on; outer end 3 px further
   down the outline. *Meantime:* proposed. Thin red = v4 in
   `docs/images/ear_left_pixels.png`.
22. **[ANSWERED 2026-11-11: the haze is the tuft's little fuzz, part of the tuft; don't forget it when building him.]** **The tuft's spike tips.** The tuft's lower edge now follows each of its
   hanging spikes at the photo's exact edge (half-opaque level), so the tips
   are in. Below them, mostly under the right half (x 535-575, y 1220-1232),
   there's a faint gray haze of hair tips, only partly opaque. *Meantime:* left
   out of the tuft; by the guide they'd be wisps (thin hairs below), traced in
   the wisp step. Should they be part of the tuft instead?
23. **[ANSWERED 2026-11-11: looks good.]** **Tuft fuzz band.** Recorded below the spike tips down to where the haze
   fades (coverage 0.10, the middle of three levels tried), tapering to nothing
   at each peet. *Meantime:* proposed; picture `docs/images/tuft_fuzz.png`.
24. **[ANSWERED 2026-11-11: judgment calls make sense; classify everything.]** **What counts as a wisp vs a fringe tip.** Your guide: a wisp reaches
   *clearly* past the fringe. I use 6 px past the intermediate fur's outer edge;
   hairs poking out less than that stay with the fringe as its tips (like the
   tuft's fuzz stays with the tuft). Many tiny pieces fall below it.
25. **[ANSWERED 2026-11-11: judgment calls make sense; classify everything.]** **Wisps vs whiskers.** Long (>= 40 px), straight (>= 95%) and fairly dark
   (>= 40% opacity) = whisker, done in the last step; everything else past the
   fringe = wisp. In region 1 that makes 6 whiskers (incl. the eyebrow whiskers
   from his left ear and a loose whisker section) and 5 wisps. Right split?
26. **[ANSWERED 2026-11-11: judgment calls make sense; classify everything.]** **Very faint wisp S07** (17% opacity, ~10 px, at x 847, y 481): keep it as a
   wisp, or treat it as fringe fuzz?
27. **[ANSWERED 2026-11-11: whiskers are light; dark ones aren't whiskers → stay wisps. Measured: none is actually dark; my "dark" meant opacity.]** **Six borderline wisps:** dark, very straight, 30-37 px (just under the 40 px
   whisker length): B2-S09, B2-S14, B2-S17, B4-S01 at cheek/mouth height (your
   guide puts whiskers there), B2-S32, B2-S34 lower on his side. *Meantime:*
   wisps; I'll re-check the four at cheek/mouth height when I do the whiskers,
   next to the full whiskers.
28. **The rogue wisp** above his right eye: confirmed against the outline from
   before the bridge (the bump was exactly this hair's base); traced as one hair
   across a whisker crossing (B5-S07). Picture `docs/images/rogue_wisp_pixels.png`.
29. [ANSWERED by measurement 2026-11-14: the fan is three whiskers; each has its own line; B4-S12/S15 run under the fur along FW-05.] **Shared whisker roots** (his right-side fan, image left): measured darkness
   says three whiskers (B4-S12, B4-S17, B4-S15) lie on one line near the root;
   each now has its own line through the shared stretch. *Meantime:* as traced;
   picture `docs/images/whiskers_3.png`.
30. [ANSWERED 2026-11-14: B2-S29 is the outer part of B2-S20; B1-S07 continued on its own arc to his brow (82 px inferred), eye step to confirm.] **Loose whisker sections** B1-S07 (beside his left eye) and B2-S29 (left side,
   low): their link back to his head is too faint to see. *Meantime:* traced as
   what's visible, classified whisker.
31. [ANSWERED 2026-11-14: continued on its own arc to his brow (25 px inferred), eye step to confirm.] **B5-S06** (long eyebrow whisker above his right eye) stops ~10 px short of his
   fur where it crosses the rogue wisp. *Meantime:* left for the lash/eye step,
   which works in that area anyway.
32. **Face whiskers, fourth pass (2026-11-14):** 18 traced (12 before + L01-L04,
   L06, L07 = FW-07..FW-12, per your answer). Pictures: the line view
   `docs/images/face_whiskers_lineview_image_left.png` / `..._right.png`; the photo
   `face_whiskers_image_left.png` / `..._right.png`; one zoom per whisker
   `face_whisker_<id>.png`; the views compared `face_whiskers_views_compared.png`.
33. **B2-S02's face line is linked by position.** *Meantime:* linked.
34. **His right-side fan (B4-S12/S15/S17):** FW-05 was found from that shared root;
   which of the three it is I can't tell. B2-S12, B2-S15, B2-S20 still show no face part.
35. **[ANSWERED 2026-11-14: all are whiskers; continuations are parts of the same whisker.]**
   L05, L08-L11 are FW-13..FW-17; L12-L19 joined into B5-S17, FW-07, FW-06, B2-S08, B2-S16,
   FW-10, FW-12, B2-S02 (each refitted as one arc; FW-12's photo fits lie 2.7 px from its arc,
   the others 0.7-1.5 px). Sheets kept: `docs/images/candidates/`.
36. **[ANSWERED 2026-11-14: trace them to the pads now; whiskers don't just cut off.]** Done:
   `docs/WHISKER_MAP.md`, `docs/images/whiskers_full/whiskers_full.pdf`.
37. **[ANSWERED 2026-11-14: fine.]** FW-02 and FW-13 end at his outline.
38. **[ANSWERED by measurement 2026-11-14.]** Joins in `docs/WHISKER_MAP.md`.
39. **[ANSWERED 2026-11-14: "a pretty good pad outline".]**
40. **[ANSWERED 2026-11-14: bends are fine; FW-14 was two whiskers -> FW-14 and FW-19; FW-19's curve
   is fine: "a consistent curve, that I could imagine a whisker actually making".]**
41. **[ANSWERED 2026-11-14: a whisker reaching the edge of his face goes past it, then "either goes
   backwards or stays with the fluff".]** Checked: none of the eight carries on straight into the fringe
   (its straight line there is no darker than the fringe beside it), which fits. Recorded as their outer
   ends; build checklist updated. Whiskers that stop mid-cheek while dark (FW-08, FW-09, FW-10, FW-12,
   FW-15) stay "dips under the fur".
42. **[ANSWERED 2026-11-14: C06, C08 not whiskers -> Bnuy Perturbances BP-02, BP-03 (with C03 -> BP-01);
   C12 is a whisker -> FW-18.]**
43. **[APPROVED 2026-11-15: head line, fold and ear strip saved to `data/lines/body_parts_lines.json`.]**
   **Head / Intermediate Bnuy / Undercarriage (2026-11-15), drawn guess:** `docs/images/body_parts/
   proposal_body.png` and `proposal_zoom.png`. Where his head ends (magenta): along the dark line under his
   mouth, then up each cheek crease (solid where I can see it, about 150 px from each mouth corner), then
   carried straight on to his edge (dashed), meeting it at about y 667 (image left) and y 647 (image right).
   The lower fold (blue), as you agreed. Is the head line right, especially where the dashed parts meet
   his edge?
   **Update (2026-11-15):** you agreed with the three parts; the middle stretch moved down to run under his
   whole mouth (it had followed the lip and split it into two zones): one gentle line from just under each
   mouth corner, no bump in the middle; his nose, under-nose cheeks, pads and both lips are all in the head
   (pads clear it by >= 13 px). Pictures updated.
   **Update 2 (2026-11-15):** your two small changes. (1) "His right side" read as the picture's right
   (it was the one going higher: it met his edge at y 647 vs y 667): that cheek line is now the mirror of
   the picture's-left one, and both meet his edge at the same height (y 667). His face is tipped a few
   degrees in this photo (picture-right nostril wing 16 px and lip corner 22 px higher), so the mirrored
   line starts 28 px higher under that mouth corner and takes that up gently along the cheek. If you meant
   the other side, or want the tilt kept at his edge, say so. (2) Your-left (grey) peet: 910 px inside
   the approved peet parts were coloured undercarriage (the approved peet line stopped short of his edge
   at x 785); now the approved peet parts always win and the line is carried on to his edge: 0 px of
   undercarriage inside either peet. Same cause checked everywhere: your ears were being coloured as head
   (out of sight above the old pictures); fixed the same way, now green, and the overview shows his whole
   body. Is the head line now right?
   **Update 3 (2026-11-15):** your two changes. (1) Under his mouth the line now stays flat (level with
   where the picture-left diagonal evens out) and joins the mirrored diagonal: the whole head line is
   symmetric about one upright line (x 553.7; mirror mismatch <= 0.6 px), both ends at y 666.5. (2) His
   ears are joined by a thin strip (4 px) along the top of his head between them, like his peets.
44. **3D grounding, steps 1-3 (2026-11-16), first pass:** `docs/SPACE.md`, the room in 3D
   `docs/space/room.html`, pictures `docs/images/space/`. (a) Are the 27 landmarks right
   (`docs/images/space/landmarks.png`, eyes `landmarks_eyes.png`)? Each eye's centre is from an oval fitted
   to the eyeball's sides; where the eyeball meets the lashes there is no light-dark edge, so its top is
   carried on from the sides (±4 px; the eye step draws the eye itself). (b) The anchor camera is
   PROVISIONAL: to replace the placeholders we need any of: the phone model and zoom and whether the
   photo was cropped (or the focal length from the original's photo info: just the numbers); his real
   width across his widest point; roughly how high and far the phone was; or a sheet of paper flat where
   he sat, photographed from the same spot and zoom.
   **Partly answered (2026-11-16):** phone settings unknown; ≤ six inches away; straight on, a touch below
   his eye level, looking level or very slightly up; the picture was cropped. Owner's method: fix the
   camera like that and determine how he is being looked at. Still open: his real size (fixes the lens).
   **Done (2026-11-16):** camera placed so (level, 13 cm, his eyes a touch above it, aimed at his face);
   he is tipped ~5 deg (his left side up) and turned ~5-9 deg toward his left (`docs/images/space/facing.png`).
   Still open: his real size: his width across his widest point, or his height to the top of his head.
   **Answered (2026-11-16):** "roughly 6 inches away from the camera"; size check "is this the size of a
   little fluffy rabbit?" -> the shortest lens that fits; he is about 12.3 cm wide, 10.5 cm to the top of
   his head. A tape measure would still confirm it (optional).
   **Corrected (2026-11-16):** owner: too small, he's an adult; size floor: the top of
   his head >= 12.7 cm -> camera 2.4 cm below his eyes; he is about 15.5 cm wide, 12.7 cm to the top of
   his head (at the floor; maybe a little bigger).
   **[ANSWERED 2026-11-16: "those numbers seem to fit him"; no tape measure.]**

45. **Depth lines (2026-11-16), first pass:** `docs/images/space/depth_lines.png` (rings every 1 cm of height,
   slices every 1 cm going back), `depth_side.png`, `depth_top.png`, `depth_behind.png`, and in 3D
   `docs/space/room.html`. (a) Do the lines look like him going back? (b) How far back does he go: is he
   about as long front to back as he is wide when he loafs, or longer? (Drawn round for now.) A side photo
   of him loafing would measure it.
   **Owner (2026-11-16):** "the resulting shape is very very flat ... you kept the actual part where depth
   was important flat". Logged (lesson 28); see Q46.
46. **The middle of his face is still flat (2026-11-16).** Measured, cm behind his nose: nostril wings 0.3,
   mouth corners 0.0, chin 0.0, chest 0.2 (eyes 2.4-2.6, top of head 4.5). From this one photo how far back
   his chin and chest sit is not settled. Ways to settle it: (a) a side photo of him (profile, any angle
   near it; he can be loafing anywhere): measures it directly; (b) your guidance, e.g. how far his nose
   sticks out past his chest, or a rough side sketch, marked owner-guided; (c) I try reading his midline's
   light alone (forehead bright, under the muzzle dark) for its slope: objective but assumes light from above.
   **[CLOSED 2026-11-16: Q45 and Q46: the depth approach was scrapped by the owner ("I dislike this. Scrap it,
   lemme think of another method"); no side photos (see DECISIONS, "He is not static").]**
