import os
import numpy as np
import nibabel as nib
from nilearn import datasets, image, plotting
from matplotlib.colors import ListedColormap

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

LESION_REGIONS = [
    ("Amygdala", "both", (55, 126, 184, 255)),
    ("Hippocampus", "right", (228, 26, 28, 255)),
    ("Hippocampus", "left", (228, 26, 28, 150)),
    ("Temporal Pole", "both", (255, 127, 0, 255)),
    ("Superior Temporal Gyrus, anterior division", "both", (255, 150, 50, 255)),
    ("Middle Temporal Gyrus, anterior division", "both", (255, 150, 50, 255)),
    ("Inferior Temporal Gyrus, anterior division", "both", (255, 150, 50, 255)),
    ("Temporal Fusiform Cortex, anterior division", "both", (255, 150, 50, 255)),
    ("Parahippocampal Gyrus, anterior division", "both", (255, 150, 50, 255))
]

LEGEND = {
    "Hippocampus (Right Total, Left Anterior)": "#e41a1c",
    "Amygdala (Bilateral)": "#377eb8",
    "Anterior Temporal Lobe & Medial Cortex": "#ff7f00"
}

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

    if np.sum(mask_data) == 0: return nib.Nifti1Image(mask_data, atlas_img.affine)

    if not any(l.lower().startswith(("left ", "right ")) for l in labels if name_substring.lower() in l.lower()):
        if hemisphere in ("right", "left"):
            x_size = atlas_data.shape[0]
            mid = x_size // 2
            hem_mask = np.zeros_like(mask_data, dtype=bool)
            if hemisphere == "right": hem_mask[:mid, :, :] = True
            else: hem_mask[mid:, :, :] = True
            mask_data[~hem_mask] = 0

    return nib.Nifti1Image(mask_data, atlas_img.affine)

def build_lesion_map(sub_atlas, cort_atlas):
    sub_img = sub_atlas.maps
    cort_img = cort_atlas.maps
    sub_labels = sub_atlas.labels
    cort_labels = cort_atlas.labels
    ref_img, scalar_data = None, None

    for i, (region, hemi, _rgba) in enumerate(LESION_REGIONS, start=1):
        mask = extract_region(sub_img, sub_labels, region, hemi)
        if np.sum(mask.get_fdata()) == 0: mask = extract_region(cort_img, cort_labels, region, hemi)
        
        if np.sum(mask.get_fdata()) == 0: continue

        if ref_img is None:
            ref_img = mask
            scalar_data = np.zeros(mask.shape, dtype=np.float32)

        mask_r = image.resample_to_img(mask, ref_img, interpolation="nearest")
        mdata = np.asarray(mask_r.get_fdata(), dtype=bool)
        # ONLY update voxels that haven't been assigned yet (prevent overwriting)
        scalar_data[(mdata) & (scalar_data == 0)] = i

    return nib.Nifti1Image(scalar_data, ref_img.affine, ref_img.header)

def make_legend_html():
    # Group regions by color for a cleaner legend
    seen_colors = {}
    for i, (name, hemi, rgba) in enumerate(LESION_REGIONS, start=1):
        color_hex = '#{:02x}{:02x}{:02x}'.format(rgba[0], rgba[1], rgba[2])
        # Grouping logic: name the group by the first region that uses this color
        if color_hex not in seen_colors:
            if "Hippocampus" in name:
                display_name = "Hippocampus (R: Total, L: Anterior)"
            elif "Amygdala" in name:
                display_name = "Amygdala (Bilateral)"
            elif "Temporal Pole" in name:
                display_name = "Anterior Temporal Pole (Hub)"
            elif "Gyrus" in name or "Cortex" in name:
                display_name = "Lateral & Inferior Temporal Cortex"
            else:
                display_name = name
            seen_colors[color_hex] = display_name
        
    items = "".join(f'<div style="display:flex;align-items:center;gap:12px;margin:10px 0">'
                    f'<div style="width:24px;height:24px;border-radius:4px;background:{colour};flex-shrink:0"></div>'
                    f'<span style="font-weight:600; font-size:15px;">{label}</span></div>' for colour, label in seen_colors.items())
    return f"""
    <div id="lesion-legend" style="position:fixed;bottom:40px;right:40px;background:rgba(15,23,42,0.92);
         border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:24px 30px; backdrop-filter: blur(12px);
         font-family:-apple-system, system-ui, sans-serif;color:#f8fafc;z-index:9999;max-width:380px;box-shadow: 0 15px 50px rgba(0,0,0,0.6);">
      <div style="font-weight:800;font-size:22px;margin-bottom:12px;color:#38bdf8;letter-spacing:-0.025em">
        J.B.R. Lesion Map
      </div>
      {items}
    </div>"""

def get_responsive_patch():
    return """
<style>
    body { background: transparent !important; margin: 0; padding: 0; overflow: hidden; height: 100vh; }
    #view-canvas { width: 100%; height: 100vh !important; }
    
    @media (max-width: 1024px) {
        #lesion-legend { display: none !important; }
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

def export_view(lesion_img, output_path):
    print(f"Generating view → {output_path}")
    
    from matplotlib.colors import ListedColormap
    # Add a transparent color for index 0 (background)
    colors_list = [[0, 0, 0, 0]] 
    for _, _, rgba in LESION_REGIONS:
        colors_list.append([c/255.0 for c in rgba])
    
    custom_cmap = ListedColormap(colors_list)
    
    # We set vmin=0 and vmax=len(LESION_REGIONS) to ensure 
    # Index 1 is always the 2nd color (Blue), Index 2 is 3rd (Red), etc.
    html_view = plotting.view_img(lesion_img, bg_img="MNI152", threshold=0.5, colorbar=False,
                                 title="J.B.R. Lesion Map", cmap=custom_cmap, 
                                 vmin=0, vmax=len(LESION_REGIONS), symmetric_cmap=False)
    
    html_view.save_as_html(output_path)
    
    with open(output_path, "r") as f:
        full_html = f.read()

    full_html = full_html.replace("var brain = brainsprite", "window.brain = brainsprite")
    full_html = full_html.replace('"crosshair": true', '"crosshair": false')
    custom_ui = f"{get_responsive_patch()}\n{make_legend_html()}"
    
    if "</body>" in full_html:
        full_html = full_html.replace("</body>", f"{custom_ui}</body>")
    else:
        full_html += custom_ui

    if "<head>" in full_html:
        full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')

    with open(output_path, "w") as f:
        f.write(full_html)

if __name__ == "__main__":
    sub_atlas, cort_atlas = fetch_atlases()
    lesion_img = build_lesion_map(sub_atlas, cort_atlas)
    export_view(lesion_img, os.path.join(OUTPUT_DIR, "jbr_damage.html"))