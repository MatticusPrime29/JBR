import os
import numpy as np
import nibabel as nib
from nilearn import datasets, image, plotting
from matplotlib.colors import ListedColormap

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Specialized white matter tracts from Juelich atlas
REGIONS = [
    ("WM Uncinate fascicle", "both", (255, 255, 255, 255)), # Bright White
    ("WM Inferior occipito-frontal fascicle", "both", (0, 191, 255, 255)), # Deep Sky Blue
    ("WM Fornix", "both", (255, 105, 180, 255)) # Hot Pink
]

def fetch_juelich():
    print("Fetching Juelich white matter atlas…")
    return datasets.fetch_atlas_juelich("maxprob-thr25-2mm")

def extract_region(atlas_img, labels, name_substring, hemisphere):
    atlas_data = np.asarray(atlas_img.get_fdata())
    mask_data = np.zeros_like(atlas_data, dtype=np.uint8)
    for idx, label in enumerate(labels):
        label_lower = label.lower()
        target = name_substring.lower()
        # Juelich labels sometimes have hemisphere info in the string
        if target in label_lower:
            if hemisphere == "both":
                mask_data[atlas_data == idx] = 1
            elif hemisphere in label_lower:
                mask_data[atlas_data == idx] = 1
    return nib.Nifti1Image(mask_data, atlas_img.affine)

def build_map(atlas):
    img, labels = atlas.maps, atlas.labels
    ref_img, scalar_data = None, None

    for i, (region, hemi, _rgba) in enumerate(REGIONS, start=1):
        mask = extract_region(img, labels, region, hemi)
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
        ('<div style="width:24px;height:24px;border-radius:4px;background:#ffffff;border:1px solid #ccc;flex-shrink:0"></div>', 'Uncinate Fasciculus'),
        ('<div style="width:24px;height:24px;border-radius:4px;background:#00bfff;flex-shrink:0"></div>', 'IFOF (ILF Proxy)'),
        ('<div style="width:24px;height:24px;border-radius:4px;background:#ff69b4;flex-shrink:0"></div>', 'Fornix (Hippocampal Output)')
    ]
    html_items = "".join(f'<div style="display:flex;align-items:center;gap:12px;margin:10px 0">{icon}<span style="font-weight:600; font-size:15px;">{label}</span></div>' for icon, label in items)
    
    return f"""
    <div id="wm-legend" style="position:fixed;bottom:40px;right:40px;background:rgba(15,23,42,0.92);
         border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:24px 30px; backdrop-filter: blur(12px);
         font-family:-apple-system, system-ui, sans-serif;color:#f8fafc;z-index:9999;max-width:380px;box-shadow: 0 15px 50px rgba(0,0,0,0.6);">
      <div style="font-weight:800;font-size:22px;margin-bottom:12px;color:#38bdf8;letter-spacing:-0.025em">
        White Matter Tracts
      </div>
      {html_items}
      <div style="margin-top:16px;font-size:13px;color:#94a3b8;line-height:1.4">
        Visualizing pathways critical for J.B.R.'s semantic and memory processing.
      </div>
    </div>"""

def get_responsive_patch():
    return """
<style>
    body { background: transparent !important; margin: 0; padding: 0; overflow: hidden; height: 100vh; }
    #view-canvas { width: 100%; height: 100vh !important; }
    
    @media (max-width: 1024px) {
        #wm-legend { display: none !important; }
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
    colors = [
        [0,0,0,0],            # 0: Transparent
        [1.0, 1.0, 1.0, 1.0], # 1: White (Uncinate)
        [0.0, 0.75, 1.0, 1.0], # 2: Sky Blue (IFOF)
        [1.0, 0.41, 0.71, 1.0] # 3: Hot Pink (Fornix)
    ]
    cmap = ListedColormap(colors)
    
    view = plotting.view_img(img, bg_img="MNI152", threshold=0.5, colorbar=False,
                            title="White Matter Tracts", cmap=cmap, vmin=0, vmax=3,
                            symmetric_cmap=False)
    view.save_as_html(output_path)
    
    with open(output_path, "r") as f: full_html = f.read()
    full_html = full_html.replace("var brain = brainsprite", "window.brain = brainsprite")
    full_html = full_html.replace('"crosshair": true', '"crosshair": false')
    full_html = full_html.replace("</body>", f"{get_responsive_patch()}{make_legend_html()}</body>")
    if "<head>" in full_html:
        full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')
    with open(output_path, "w") as f: f.write(full_html)

if __name__ == "__main__":
    atlas = fetch_juelich()
    img = build_map(atlas)
    export_view(img, os.path.join(OUTPUT_DIR, "jbr_white_matter.html"))
