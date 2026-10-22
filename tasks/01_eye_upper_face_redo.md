# Tasks: eye and upper-face stage, clean redo

Verbatim from the plan agreed with the owner. Checked off one by one, in
order. No step is simplified or skipped without the owner's explicit
permission. Re-read docs/INTENTS.md before each step and repeat it at the end
of each step.

Yes. Here is exactly what happens next, on the rolled-back kept build (d9f1d7c, restored in commit 716e530):

- [x] 1. **Draw the lines on his photos, part by part.**
   - [x] **Eye:** the black of the eye, already traced in ten photos last time; I'll check each trace again and redo any that are off.
   - [x] **Socket:** the edge of the dark eye-ring and lid round each eye.
   - [x] **Ridge:** the fold of fur over the eye.
   - [x] **Forehead:** the forehead line.
   - [x] **Muzzle:** the muzzle line.

   - [x] Each traced on a zoomed grid, in every photo where that part actually shows.
   - [x] I'll also mark the same physical points in several photos (eye corners, top of the ridge, the brow fold, nose V) to get their real 3D positions.
     (Done: nose V triangulated, consistent in the master and both three-quarters. Eye corners and the brow fold are kept as traced lines: on a round eye and in fur they are not fixed points. Owner: don't overscrutinize.)
- [ ] 2. **Draw the same lines on the model** from each photo's camera, with his head posed as he holds it there.
- [ ] 3. **Score each part's shape, orientation, depth and size in each photo, compare by eye, and check in.** I'll show you the eye and socket lines laid over his photos next to the model, with the comparison and the scores (not outline agreement). Then I stop and wait for you. No sculpting before that check-in.

**After the check-in, only if you agree:**
- [ ] **The 3D eye:** an eyeball and lid opening fitted to the traces, weighted to the master.
- [ ] **Then the other parts one at a time:** socket, ridge, forehead, muzzle. Each gets small, local changes. After each one I compare the render to his photo from the same angle and roll it back myself if it isn't closer to him. The other angles get agreeing first without holding the front rigid, then the result is made to look like the master. No deforming the overall head.
   - [ ] Socket
   - [ ] Ridge
   - [ ] Forehead
   - [ ] Muzzle

All of it follows `docs/INTENTS.md`, which I re-read and repeat at the end of every step. Nothing gets simplified without your explicit permission. If anything is unclear or seems impossible, I stop and ask.

Say "start" and I'll begin with step 1.
