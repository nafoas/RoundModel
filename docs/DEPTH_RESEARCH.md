# Depth from one photo: research (2026-11-16)

Owner: "research the most objective way to discern depth from a 2D image. Maybe we just need a new perspective."
Context: the hand-built approach (a blob shell fitted to his outline, then depth read from his fur's shading
under a hand-modelled light) was scrapped: rigid assumptions everywhere, a flat face, then a lopsided one.
Photo: `data/photos/anchor_front.webp` (the only one; no extra angles, see DECISIONS "He is not static").

## 1. Why the classic methods failed us (and always would, on one photo)

- **One photo does not fix depth on its own.** Shape from shading is underconstrained: it needs the
  material and the light to be known, and even then a flattened relief can produce the same picture as a
  deep surface (the "bas-relief ambiguity", Belhumeur et al.), and a surface and its inside-out can look
  the same. That is exactly what happened: flat face, then a face tilted toward the light.
  ([Barron & Malik 2012](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/reconstruction/BarronMalikCVPR2012.pdf),
  [Barron & Malik 2011](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/reconstruction/BarronMalikCVPR2011.pdf),
  [On Shape from Shading](https://freddy.cs.technion.ac.il/wp-content/uploads/2018/01/On-Shape-from-Shading.pdf),
  [Belhumeur et al.](https://core.ac.uk/download/50177805.pdf))
- **The outline only helps at the edge** (there the surface is edge-on); the inside has to come from
  somewhere else ([Richter & Roth 2015](https://openaccess.thecvf.com/content_cvpr_2015/papers/Richter_Discriminative_Shape_From_2015_CVPR_paper.pdf)).
- Every way around that ambiguity in the classic methods is a hand-made assumption (a light model, a
  symmetry, a smoothness, a shape family): the rigidity the owner warned about.

## 2. What the field uses now: depth models learned from millions of real photos

These are not hand-made rules: they have learned what depth looks like from very large, varied collections of
real and synthetic images (people, animals, objects, close-ups). They work on one photo at a time and assume
no symmetry and no light model. The current leaders:

| Model | What it gives | Notes |
|---|---|---|
| **Depth Pro** (Apple, ICLR 2025) | depth in real units + the camera's focal length, from the photo alone; very sharp edges | its distance and lens are an independent check of the owner's "six inches" ([paper](https://arxiv.org/html/2410.02073v1), [Apple](https://machinelearning.apple.com/research/depth-pro), [weights](https://huggingface.co/apple/DepthPro/blob/main/README.md)) |
| **MoGe / MoGe-2** (Microsoft, CVPR 2025 oral) | a 3D point for every pixel, the camera's field of view, and (MoGe-2) surface directions | leads several surface-direction benchmarks ([paper](https://arxiv.org/abs/2410.19115), [Marigold V2 comparison](https://arxiv.org/pdf/2609.08084)) |
| **Depth Anything 3** (ByteDance, Nov 2025) | depth (relative and metric versions) | newest of the widely used families ([blog](https://seed.bytedance.com/en/blog/depth-anything-3-a-single-transformer-architecture-for-space-reconstruction-from-any-views), [Roboflow](https://blog.roboflow.com/depth-anything-3/)) |
| Surface-direction models (DSINE, StableNormal, Lotus) | which way each spot faces | the thing the shading approach tried to read by hand ([StableNormal](https://arxiv.org/pdf/2406.16864), [GeoBench](https://alphaxiv.org/benchmarks/tsinghua-university/geobench)) |

Still open in the field (honest limits): no benchmark tests fur or close-ups specifically
([Koch et al.](https://openaccess.thecvf.com/content_ECCVW_2018/papers/11131/Koch_Evaluation_of_CNN-based_Single-Image_Depth_Estimation_Methods_ECCVW_2018_paper.pdf));
papers rank themselves on different benchmarks, so there is no single winner
([2026 survey](https://arxiv.org/pdf/2609.01172), [MD2E, CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/papers/Ning_MD2E_Modeling_Depth-to-Edge_Cues_for_Monocular_Metric_Depth_Estimation_CVPR_2026_paper.pdf),
[SciTePress 2026 comparison](https://www.scitepress.org/Papers/2026/142618/142618.pdf)); and nothing sees his back from a
front photo. Whole-object generators (e.g. Meta's [SAM 3D](https://blog.roboflow.com/sam-3d/)) invent the hidden
back: not measurements.

## 3. The most objective method available: several independent models, checked against what we know

No single model is the truth. Objectivity comes from **independent witnesses agreeing**:
1. Run 2-3 of the leaders above (different makers, different training) on the anchor photo.
2. Put each one's surface into the room (as done, owner 2026-11-16: through each model's OWN camera, since
   each model's distances only fit its own lens; see `docs/SPACE.md`).
3. **Check each against what we already know and they were not told**: his nose at about six inches (Depth
   Pro and MoGe estimate distance and lens themselves), his approved size, his outline (the surface must be
   edge-on there), his head's tilt.
4. **Where they agree, it is measured; where they disagree, show it**, and the owner's eye decides.
These are MEASUREMENTS of his visible surface (like the masks, rule 1), never the model. They do not assume
he is symmetric or still, so a photo of him leaning or with squashed fur is just that photo.

Runs here on CPU (no graphics card): a few minutes per model for one photo; weights download from Hugging
Face (reachable). Licences to respect: MoGe MIT; Depth Anything 3 small/base Apache 2.0, large CC BY-NC;
Depth Pro Apple's sample-code licence. Weights are not committed.
