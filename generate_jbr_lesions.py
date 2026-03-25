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
    ("Temporal Fusiform Cortex, posterior division", "both", (255, 150, 50, 255)),
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

def export_view_slice(lesion_img, output_path):
    """Generates the Brainsprite-based slice viewer."""
    print(f"Generating Slice view → {output_path}")
    colors_list = [[0, 0, 0, 0]] 
    for _, _, rgba in LESION_REGIONS:
        colors_list.append([c/255.0 for c in rgba])
    
    custom_cmap = ListedColormap(colors_list)
    html_view = plotting.view_img(lesion_img, bg_img="MNI152", threshold=0.5, colorbar=False,
                                 title="J.B.R. Lesion Map - Slices", cmap=custom_cmap, 
                                 vmin=0, vmax=len(LESION_REGIONS), symmetric_cmap=False)
    html_view.save_as_html(output_path)
    
    with open(output_path, "r") as f:
        full_html = f.read()

    full_html = full_html.replace("var brain = brainsprite", "window.brain = brainsprite")
    full_html = full_html.replace('"crosshair": true', '"crosshair": false')
    custom_ui = f"{get_responsive_patch()}\n{make_legend_html('Slice View (Subcortical)')}"
    
    if "</body>" in full_html:
        full_html = full_html.replace("</body>", f"{custom_ui}</body>")
    
    if "<head>" in full_html:
        full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')

    with open(output_path, "w") as f:
        f.write(full_html)

def get_responsive_patch():
    return """
<style>
    body { background: transparent !important; margin: 0; padding: 0; overflow: hidden; height: 100vh; width: 100vw; display: flex; align-items: center; justify-content: center; }
    canvas { touch-action: none; display: block; }
</style>
<script>
window.addEventListener('message', function(e) {
    if (e.data && e.data.axis) {
        const canvas = document.getElementById('3Dviewer');
        if (!canvas) return;
        const b = window.brain;
        if (!b || !b.widthCanvas) return;
        
        // Use the actual slice dimensions for the current axis
        const tW = (e.data.axis === 'X') ? b.widthCanvas.X : (e.data.axis === 'Y' ? b.widthCanvas.Y : b.widthCanvas.Z);
        const tH = b.heightCanvas.max;
        
        canvas.style.transformOrigin = 'center center';
        canvas.style.transition = 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        
        let winW = window.innerWidth;
        let winH = window.innerHeight;
        
        // Fixed scale: No more aggressive zooming
        canvas.style.transform = `scale(0.95)`;
    }
});
</script>
"""

def export_view_surf(lesion_img, output_path):
    """Generates the high-quality 3D surface viewer."""
    print(f"Generating Surface view → {output_path}")
    
    colors_list = [[0, 0, 0, 1.0]] # First is transparent-ish background
    for _, _, rgba in LESION_REGIONS:
        colors_list.append([c/255.0 for c in rgba])
    custom_cmap = ListedColormap(colors_list)

    # Use view_img_on_surf for a beautiful 3D cortical view
    html_view = plotting.view_img_on_surf(lesion_img, surf_mesh='fsaverage5', threshold=0.5,
                                         cmap=custom_cmap, colorbar=False, 
                                         vmin=0, vmax=len(LESION_REGIONS),
                                         title="J.B.R. Lesion Map - 3D Surface")
    
    html_view.save_as_html(output_path)
    
    with open(output_path, "r") as f:
        full_html = f.read()

    # Simplify UI for surface: no need for brainsprite patch, just centering and legend
    custom_style = """
<style>
    body { background: #000 !important; margin: 0; padding: 0; overflow: hidden; }
    canvas { outline: none !important; }
</style>
<script>
    // Nilearn surface views just work usually, but let's ensure meta tags
    window.addEventListener('message', function(e) {
        // Surface view doesn't handle axis, but we listen to prevent errors
    });
</script>
"""
    custom_ui = f"{custom_style}\n{make_legend_html('3D Surface View')}"
    
    if "</body>" in full_html:
        full_html = full_html.replace("</body>", f"{custom_ui}</body>")
    
    if "<head>" in full_html:
        full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')

    with open(output_path, "w") as f:
        f.write(full_html)

def make_legend_html(subtitle=""):
    seen_colors = {}
    for name, hemi, rgba in LESION_REGIONS:
        color_hex = '#{:02x}{:02x}{:02x}'.format(rgba[0], rgba[1], rgba[2])
        if color_hex not in seen_colors:
            if "Hippocampus" in name: display_name = "Hippocampus (R: Total, L: Anterior)"
            elif "Amygdala" in name: display_name = "Amygdala (Bilateral)"
            elif "Temporal Pole" in name: display_name = "Anterior Temporal Pole (Hub)"
            elif "Fusiform" in name: display_name = "Fusiform Gyrus"
            elif "Gyrus" in name or "Cortex" in name: display_name = "Lateral & Inferior Temporal Cortex"
            else: display_name = name
            seen_colors[color_hex] = display_name
        
    items = "".join(f'<div style="display:flex;align-items:center;gap:12px;margin:10px 0">'
                    f'<div style="width:20px;height:20px;border-radius:4px;background:{colour};border:1px solid rgba(255,255,255,0.2)"></div>'
                    f'<span style="font-weight:500; font-size:14px; color:#e2e8f0">{label}</span></div>' for colour, label in seen_colors.items())
    
    return f"""
    <div id="lesion-legend" style="position:fixed;bottom:120px;left:50%;transform:translateX(-50%);background:rgba(15,23,42,0.85);
         border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:16px 24px; backdrop-filter: blur(20px);
         font-family:system-ui, -apple-system, sans-serif;z-index:9999;width:85%;max-width:320px;box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
      <div style="font-weight:800;font-size:18px;margin-bottom:2px;color:#38bdf8;letter-spacing:-0.01em">J.B.R. Lesion Map</div>
      <div style="font-size:11px;font-weight:600;color:#94a3b8;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px">{subtitle}</div>
      {items}
    </div>"""

if __name__ == "__main__":
    sub_atlas, cort_atlas = fetch_atlases()
    lesion_img = build_lesion_map(sub_atlas, cort_atlas)
    
    # Generate Slices
    export_view_slice(lesion_img, os.path.join(OUTPUT_DIR, "jbr_damage_slices.html"))
    # Generate Surface
    export_view_surf(lesion_img, os.path.join(OUTPUT_DIR, "jbr_damage.html"))