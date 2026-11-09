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
17. **Where each ear meets his head** (`docs/images/ear_bases_proposed.png`,
   zoom `ear_bases_zoom.png`). Ear on image right: a clear crease, followed;
   its inner end is where the dip between the ears starts rising, its outer end
   where the crease meets the ear's shaded outer side (y 308; the outline has a
   very slight kink higher up at y 254 that I did NOT use). Ear on image left:
   the crease is faint; the line runs from the ear's outer corner to the bottom
   of its step into the dip, so the small ledge belongs to the ear. The flat dip
   between them is the top of his head. *Meantime:* proposed; the two bases
   aren't symmetric (right one ~20 px lower outside), left as the photo shows.
