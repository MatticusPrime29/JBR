import os
import numpy as np
import nibabel as nib
from nilearn import datasets, image, plotting
from matplotlib.colors import ListedColormap

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Specialized regions for Perirhinal view
REGIONS = [
    ("Parahippocampal Gyrus, anterior division", "both", (255, 165, 0, 255)), # Orange
    ("Hippocampus", "both", (228, 26, 28, 100)) # Faint Red for context
]

def fetch_atlases():
    print("Fetching Harvard-Oxford atlases…")
    sub = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm")
    cort = datasets.fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm")
    return sub, cort

def extract_region(atlas_img, labels, name_substring, hemisphere):
    atlas_data = np.asarray(atlas_img.get_fdata())
    mask_data = np.zeros_like(atlas_data, dtype=np.uint8)
    for idx, label in enumerate(labels):
        label_lower = label.lower()
        target = name_substring.lower()
        has_prefix = label_lower.startswith("left ") or label_lower.startswith("right ")

        if has_prefix:
            prefix = "right " if hemisphere == "right" else "left "
            if hemisphere == "both":
                if target in label_lower: mask_data[atlas_data == idx] = 1
            else:
                if label_lower.startswith(prefix) and target in label_lower[len(prefix):]:
                    mask_data[atlas_data == idx] = 1
        else:
            if target in label_lower: mask_data[atlas_data == idx] = 1

    return nib.Nifti1Image(mask_data, atlas_img.affine)

def build_map(sub_atlas, cort_atlas):
    sub_img, sub_labels = sub_atlas.maps, sub_atlas.labels
    cort_img, cort_labels = cort_atlas.maps, cort_atlas.labels
    ref_img, scalar_data = None, None

    for i, (region, hemi, _rgba) in enumerate(REGIONS, start=1):
        mask = extract_region(sub_img, sub_labels, region, hemi)
        if np.sum(mask.get_fdata()) == 0: mask = extract_region(cort_img, cort_labels, region, hemi)
        
        num_voxels = np.sum(mask.get_fdata() > 0)
        print(f"Region {i} ({region}): {num_voxels} voxels found")
        if num_voxels == 0: continue

        if ref_img is None:
            ref_img = mask
            scalar_data = np.zeros(mask.shape, dtype=np.float32)

        mask_r = image.resample_to_img(mask, ref_img, interpolation="nearest")
        mdata = np.asarray(mask_r.get_fdata(), dtype=bool)
        scalar_data[(mdata) & (scalar_data == 0)] = i

    return nib.Nifti1Image(scalar_data, ref_img.affine, ref_img.header)

def make_legend_html():
    items = [
        ('<div style="width:24px;height:24px;border-radius:4px;background:#ffa500;flex-shrink:0"></div>', 'Perirhinal Cortex (ATL Hub)'),
        ('<div style="width:24px;height:24px;border-radius:4px;background:rgba(228,26,28,0.5);border:1px solid #e41a1c;flex-shrink:0"></div>', 'Hippocampus (Reference)')
    ]
    html_items = "".join(f'<div style="display:flex;align-items:center;gap:12px;margin:10px 0">{icon}<span style="font-weight:600; font-size:15px;">{label}</span></div>' for icon, label in items)
    
    return f"""
    <div id="perirhinal-legend" style="position:fixed;bottom:40px;right:40px;background:rgba(15,23,42,0.92);
         border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:24px 30px; backdrop-filter: blur(12px);
         font-family:-apple-system, system-ui, sans-serif;color:#f8fafc;z-index:9999;max-width:380px;box-shadow: 0 15px 50px rgba(0,0,0,0.6);">
      <div style="font-weight:800;font-size:22px;margin-bottom:12px;color:#fbbf24;letter-spacing:-0.025em">
        Perirhinal Cortex
      </div>
      {html_items}
      <div style="margin-top:16px;font-size:13px;color:#94a3b8;line-height:1.4">
        Focus: Anterior Parahippocampal Gyrus (Y ≈ -8)
      </div>
    </div>"""

def get_responsive_patch():
    return """
<style>
    body { background: transparent !important; margin: 0; padding: 0; overflow: hidden; height: 100vh; }
    #view-canvas { width: 100%; height: 100vh !important; }
    
    @media (max-width: 1024px) {
        #perirhinal-legend { display: none !important; }
    }

</style>
<script>
window.addEventListener('message', function(e) {
    if (e.data && e.data.axis) {
        const canvas = document.getElementById('3Dviewer');
        if (!canvas) return;
        const b = window.brain;
        if (!b || !b.widthCanvas) return;
        
        let maxW = window.innerWidth;
        const tX = b.widthCanvas.X;
        const tY = b.widthCanvas.Y;
        const tZ = b.widthCanvas.Z;
        
        canvas.style.transformOrigin = '0 50%';
        canvas.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        
        if (e.data.axis === 'X') {
             let scale = maxW / tX;
             canvas.style.transform = `translateY(-30%) scale(${scale}) translateX(0px)`;
        } else if (e.data.axis === 'Y') {
             let scale = maxW / tY;
             canvas.style.transform = `translateY(-30%) scale(${scale}) translateX(-${tX}px)`;
        } else if (e.data.axis === 'Z') {
             let scale = maxW / tZ;
             canvas.style.transform = `translateY(-30%) scale(${scale}) translateX(-${tX + tY}px)`;
        }
    }
});
</script>
"""

def export_view(img, output_path):
    print(f"Generating view → {output_path}")
    # Explicit 4-color map (0=bg, 1=orange, 2=red)
    colors = [
        [0, 0, 0, 0],          # 0: Transparent
        [1.0, 0.65, 0.0, 1.0], # 1: Orange (Perirhinal)
        [0.89, 0.1, 0.11, 0.5] # 2: Faint Red (Hippocampus)
    ]
    cmap = ListedColormap(colors)
    
    # We set vmin=0, vmax=2 to fix the indices
    # We also set the default cut_coords to center on the Perirhinal (y=-8)
    view = plotting.view_img(img, bg_img="MNI152", threshold=0.5, colorbar=False,
                            title="Perirhinal Cortex", cmap=cmap, vmin=0, vmax=2,
                            symmetric_cmap=False)
    
    view.save_as_html(output_path)
    
    with open(output_path, "r") as f:
        full_html = f.read()
    
    # Update script to center view by default if possible, or just inject legend
    full_html = full_html.replace("var brain = brainsprite", "window.brain = brainsprite")
    full_html = full_html.replace('"crosshair": true', '"crosshair": false')
    full_html = full_html.replace("</body>", f"{get_responsive_patch()}{make_legend_html()}</body>")
    
    if "<head>" in full_html:
        full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')
    
    with open(output_path, "w") as f:
        f.write(full_html)

if __name__ == "__main__":
    sub, cort = fetch_atlases()
    img = build_map(sub, cort)
    export_view(img, os.path.join(OUTPUT_DIR, "jbr_perirhinal.html"))
