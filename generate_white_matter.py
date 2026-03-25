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

def make_legend_html(subtitle=""):
    items = [
        ('<div style="width:20px;height:20px;border-radius:4px;background:#ffffff;border:1px solid rgba(255,255,255,0.2)"></div>', 'Uncinate Fasciculus'),
        ('<div style="width:20px;height:20px;border-radius:4px;background:#00bfff;border:1px solid rgba(255,255,255,0.2)"></div>', 'IFOF (ILF Proxy)'),
        ('<div style="width:20px;height:20px;border-radius:4px;background:#ff69b4;border:1px solid rgba(255,255,255,0.2)"></div>', 'Fornix (Hippocampal Output)')
    ]
    html_items = "".join(f'<div style="display:flex;align-items:center;gap:12px;margin:10px 0">{icon}<span style="font-weight:500; font-size:14px; color:#e2e8f0">{label}</span></div>' for icon, label in items)
    
    return f"""
    <div id="wm-legend" style="position:fixed;bottom:120px;left:50%;transform:translateX(-50%);background:rgba(15,23,42,0.85);
         border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:16px 24px; backdrop-filter: blur(20px);
         font-family:system-ui, -apple-system, sans-serif;z-index:9999;width:85%;max-width:320px;box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
      <div style="font-weight:800;font-size:18px;margin-bottom:2px;color:#38bdf8;letter-spacing:-0.01em">White Matter Tracts</div>
      <div style="font-size:11px;font-weight:600;color:#94a3b8;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px">{subtitle}</div>
      {html_items}
    </div>"""

def get_responsive_patch():
    return """
<style>
    body { background: transparent !important; margin: 0; padding: 0; overflow: hidden; height: 100vh; display: flex; align-items: center; justify-content: center; }
    canvas { touch-action: none; }
</style>
<script>
window.addEventListener('message', function(e) {
    if (e.data && e.data.axis) {
        const canvas = document.getElementById('3Dviewer');
        if (!canvas) return;
        const b = window.brain;
        if (!b || !b.widthCanvas) return;
        
        let winW = window.innerWidth;
        let winH = window.innerHeight;
        const tX = b.widthCanvas.X;
        const tY = b.widthCanvas.Y;
        const tZ = b.widthCanvas.Z;
        const tH = b.heightCanvas.max;

        canvas.style.transformOrigin = 'center center';
        canvas.style.transition = 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        
        const tW = (e.data.axis === 'X') ? b.widthCanvas.X : (e.data.axis === 'Y' ? b.widthCanvas.Y : b.widthCanvas.Z);

        // Fixed scale: No more aggressive zooming
        canvas.style.transform = `scale(0.95)`;
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
    full_html = full_html.replace("</body>", f"{get_responsive_patch()}{make_legend_html('Slice View (Subcortical)')}</body>")
    if "<head>" in full_html:
        full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')
    with open(output_path, "w") as f: f.write(full_html)

if __name__ == "__main__":
    atlas = fetch_juelich()
    img = build_map(atlas)
    export_view(img, os.path.join(OUTPUT_DIR, "jbr_white_matter.html"))
