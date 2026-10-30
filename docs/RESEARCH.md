# How others turn photos and normal maps into a whole model (research, October 2026)

Owner: "This shouldn't be as hard as it is. Read all documentation and
research some techniques, instead of just randomly coming up with ideas
using intuition and seeing if it sticks."

## What the field does

- **Per-view 2.5D maps, fused, then screened Poisson.** The standard recipe
  in multi-view photometric stereo and single-view reconstruction: for each
  photo, a depth map and a normal map of the surface that photo sees;
  every pixel becomes a 3D point with its normal (an oriented point);
  all photos' points are put in one cloud (each through its own camera);
  screened Poisson surface reconstruction (Kazhdan) turns the oriented cloud
  into one closed, smooth surface that passes through the points and
  agrees with their normals. Settings used in the papers: interpolation
  (point) weight about 4, Dirichlet boundary for closed meshes, depth 8-10.
  - Front2Back (single image): front depth+normal maps, the back predicted,
    and a reflected copy by his symmetry, fused into oriented points, then
    screened Poisson. Key observation: opposite views of a shape share the
    same silhouette (the front's edge is the back's edge).
    https://arxiv.org/pdf/1912.10589
  - MVPSNet (multi-view photometric stereo): per-view depth maps fused into
    one point cloud with predicted normals, screened Poisson (depth 8,
    weight 4). https://arxiv.org/pdf/2305.11167
  - AquaMVS: filter per-view depth maps for consistency between views, merge,
    Poisson; warns Poisson invents geometry where there are no points.
    https://aquamvs.readthedocs.io/en/latest/theory/fusion.html
  - Reference implementation: https://www.cs.jhu.edu/~misha/Code/PoissonRecon/
    (here through PyMeshLab, which runs in this environment).
- **Multi-view normal integration (SuperNormal, CVPR 2024):** a neural SDF
  fitted to normal maps from many views by volume rendering; best quality,
  but needs a GPU (hash-grid encoding). Not runnable here.
  https://openaccess.thecvf.com/content/CVPR2024/html/Cao_SuperNormal_Neural_Surface_Reconstruction_via_Multi-View_Normal_Integration_CVPR_2024_paper.html
- **Normal integration with depth jumps (BiNI, ECCV 2022; ICCV 2025
  follow-up):** single-view normal integration that keeps depth
  discontinuities (chin over chest, peets) instead of smoothing over them.
  https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/3202_ECCV_2022_paper.php ,
  https://arxiv.org/pdf/2507.06075
- **Visual hull, then refined by shading:** silhouettes alone are coarse with
  few views (faceted); refined with shading/normals for detail.
  https://bmva-archive.org.uk/bmvc/2008/papers/245.pdf ,
  https://ri.cmu.edu/?p=8658
- **Single image to 3D (TripoSR, SF3D, Hunyuan3D):** a whole mesh from one
  photo in a second on a GPU; the back is invented ("plausible rather than
  accurate"), CPU paths slow or unsupported, licences vary. Not for an
  accurate likeness. https://arxiv.org/pdf/2403.02151 ,
  https://stable-fast-3d.github.io

## What that means for Prince (why my attempts failed)

My attempts carved or extruded volumes and then tried to stitch the master's
front onto them. The field does not do that: it gathers every view's surface
as oriented points and lets one global solve (screened Poisson) make the
single closed surface that fits them all. That solve also handles the joins
(no flap, no seam) and gaps (smoothly), which is exactly where mine failed.

## Plan (proposed to the owner)

1. Per photo with a reliable camera: its normal map (have), integrated into
   a depth map of the surface it sees (perspective normal integration, as
   for the master; depth jumps kept where the photo shows an edge).
2. Each photo's relief placed in the world through its own camera (his head
   turned as re-fitted); its one free number (distance/scale) set where it
   overlaps the master's front, or for photos that don't overlap (the
   back), so its outline meets the master's edge (opposite views share the
   silhouette).
3. All reliefs as oriented points, the master's weighted highest; points
   that another photo's outline says are outside him dropped.
4. Screened Poisson (PyMeshLab): one closed surface through them all.
5. The master's front then placed exactly on its step-1 surface.
6. Checked by eye, master first, then profiles, top, back.
