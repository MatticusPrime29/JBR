"""
generate_brain_nilearn.py  —  Nilearn-based interactive brain scene generator for J.B.R.

REQUIREMENTS:
    pip install nilearn nibabel matplotlib numpy

USAGE:
    python generate_brain_nilearn.py

OUTPUT FILES (saved to this directory, auto-detected by admin.php):
    jbr_damage_nilearn.html   — Interactive 3D view of J.B.R.'s lesion on MNI template
    jbr_surface_nilearn.html  — Inflated surface rendering with lesion overlay

NOTES:
    - Uses the Harvard-Oxford atlas (human MNI space) — far more anatomically accurate
      than the previous Brainrender/Allen Mouse Brain Atlas approach.
    - Right hemisphere is primary; left included faintly where applicable.
    - On first run, Nilearn will download ~100 MB of atlas data (cached after that).
"""

import os
import numpy as np
import nibabel as nib
from nilearn import datasets, image, plotting

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── J.B.R. Lesion Map ────────────────────────────────────────────────────────
# Each entry: (region_name_substring, hemisphere, colour_value_int)
# colour_value_int is simply the scalar assigned to voxels in this region.
# Higher = rendered "hotter" in the colormap (used for visual distinction only).
# Hemisphere: 'right' | 'left' | 'both'
#
# Damage summary:
#   Right hippocampus — entirely destroyed
#   Left hippocampus  — anterior portion destroyed, posterior preserved
#   Amygdala          — bilaterally totally destroyed
#   Lateral Ventricle — bilaterally enlarged (atrophy)
#   Anterior temporal cortex — bilateral (right slightly more posterior)

LESION_REGIONS = [
    # ── Subcortical ───────────────────────────────────────────────────────────
    # Right hippocampus: entirely destroyed → full weight
    ("Hippocampus",         "right", (220,  20,  60, 255)),   # bright crimson

    # Left hippocampus: anterior only — rendered at half weight
    # (the atlas doesn't subdivide ant/post, so we use reduced opacity as a cue)
    ("Hippocampus",         "left",  (180,  20,  40, 140)),   # dimmer crimson

    # Amygdala: bilaterally totally destroyed
    ("Amygdala",            "both",  (255, 100,   0, 240)),   # orange

    # Lateral ventricles: enlarged due to atrophy (shown in a distinct cool colour)
    ("Lateral Ventricle",   "both",  ( 80, 180, 255, 160)),   # steel blue

    # ── Cortical (anterior temporal — bilateral) ──────────────────────────────
    ("Temporal Pole",                               "both",  (255, 210,   0, 220)),  # gold
    ("Superior Temporal Gyrus, anterior division",  "both",  (255, 160,  20, 200)),  # amber
    ("Middle Temporal Gyrus, anterior division",    "both",  (255, 120,  40, 190)),  # orange-amber
    ("Inferior Temporal Gyrus, anterior division",  "both",  (240,  80,  60, 180)),  # orange-red
    ("Parahippocampal Gyrus, anterior division",    "both",  (180,  30, 180, 200)),  # purple
    ("Temporal Fusiform Cortex, anterior division", "both",  (220,  60, 200, 180)),  # magenta

    # Right side extends slightly further back — posterior divisions right only
    ("Superior Temporal Gyrus, posterior division", "right", (255, 160,  20, 100)),  # faint amber
    ("Middle Temporal Gyrus, posterior division",   "right", (255, 120,  40,  90)),  # faint orange
    ("Inferior Temporal Gyrus, posterior division", "right", (240,  80,  60,  80)),  # faint orange-red
    ("Parahippocampal Gyrus, posterior division",   "right", (160,  10, 160, 100)),  # faint purple
]

LEGEND = {
    "Right Hippocampus (entirely destroyed)":       "#DC143C",
    "Left Hippocampus (anterior only)":             "#B41428",
    "Amygdala — bilateral (totally destroyed)":     "#FF6400",
    "Lateral Ventricle — bilateral (enlarged)":     "#50B4FF",
    "Temporal Pole — bilateral":                    "#FFD200",
    "Superior Temporal Gyrus ant. — bilateral":     "#FFA014",
    "Middle Temporal Gyrus ant. — bilateral":       "#FF7828",
    "Inferior Temporal Gyrus ant. — bilateral":     "#F0503C",
    "Parahippocampal Gyrus ant. — bilateral":       "#B41EB4",
    "Temporal Fusiform Cortex ant. — bilateral":    "#DC3CC8",
    "Post. temporal divisions — right only (mild)": "#FF782850",
}


def fetch_atlases():
    """Download (or load cached) Harvard-Oxford atlases."""
    print("Fetching Harvard-Oxford atlases (cached after first run)…")
    sub  = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm")
    cort = datasets.fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm")
    return sub, cort


def extract_region(atlas_img, labels, name_substring, hemisphere):
    """
    Return a binary NIfTI mask for all labels matching name_substring.

    For subcortical atlas: labels already contain 'Left '/'Right ' prefix.
    For cortical atlas:    labels have no hemisphere prefix — we use MNI x-axis
                           to spatially restrict to the correct hemisphere.
    """
    atlas_data = np.asarray(atlas_img.get_fdata())
    mask_data  = np.zeros_like(atlas_data, dtype=np.uint8)
    affine     = atlas_img.affine

    # Build the voxel mask for this label
    for idx, label in enumerate(labels):
        label_lower = label.lower()
        target      = name_substring.lower()

        has_prefix = label_lower.startswith("left ") or label_lower.startswith("right ")

        if has_prefix:
            # Subcortical-style: prefix must match hemisphere
            prefix = "right " if hemisphere == "right" else "left "
            if hemisphere == "both":
                if target in label_lower:
                    mask_data[atlas_data == idx] = 1
            else:
                if label_lower.startswith(prefix) and target in label_lower[len(prefix):]:
                    mask_data[atlas_data == idx] = 1
        else:
            # Cortical-style: match on name, then spatially mask by hemisphere
            if target in label_lower:
                mask_data[atlas_data == idx] = 1

    if np.sum(mask_data) == 0:
        return nib.Nifti1Image(mask_data, atlas_img.affine)

    # For cortical regions (no prefix), apply hemisphere spatial mask
    if not any(l.lower().startswith(("left ", "right ")) for l in labels if name_substring.lower() in l.lower()):
        if hemisphere in ("right", "left"):
            # Build spatial hemisphere mask from voxel x-coordinates
            x_size = atlas_data.shape[0]
            mid    = x_size // 2
            hem_mask = np.zeros_like(mask_data, dtype=bool)
            if hemisphere == "right":
                hem_mask[:mid, :, :] = True   # MNI: x < mid → right hemisphere
            else:
                hem_mask[mid:, :, :] = True
            mask_data[~hem_mask] = 0

    return nib.Nifti1Image(mask_data, atlas_img.affine)



def build_lesion_map(sub_atlas, cort_atlas):
    """
    Build a single 4D NIfTI where each volume represents one lesion component
    (for colour-coded display), plus a combined scalar map (value = component index).
    """
    # atlas.maps is already a Nifti1Image in this version of nilearn
    sub_img     = sub_atlas.maps
    cort_img    = cort_atlas.maps
    sub_labels  = sub_atlas.labels
    cort_labels = cort_atlas.labels

    combined_data = None
    ref_img       = None
    scalar_data   = None

    for i, (region, hemi, _rgba) in enumerate(LESION_REGIONS, start=1):
        # Try subcortical first, then cortical
        mask = extract_region(sub_img, sub_labels, region, hemi)
        if np.sum(mask.get_fdata()) == 0:
            mask = extract_region(cort_img, cort_labels, region, hemi)

        if np.sum(mask.get_fdata()) == 0:
            print(f"  ⚠  Region not found: {hemi} {region}")
            continue

        print(f"  ✓  Found {hemi} {region}")

        if ref_img is None:
            ref_img      = mask
            scalar_data  = np.zeros(mask.shape, dtype=np.float32)

        # Resample to common space if needed
        mask_r = image.resample_to_img(mask, ref_img, interpolation="nearest")
        mdata  = np.asarray(mask_r.get_fdata(), dtype=bool)
        # Use highest index for overlapping voxels (later = more opaque in legend)
        scalar_data[mdata] = i

    if ref_img is None:
        raise RuntimeError("No regions found — check atlas label names.")

    lesion_img = nib.Nifti1Image(scalar_data, ref_img.affine, ref_img.header)
    return lesion_img


def make_legend_html():
    items = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
        f'<div style="width:18px;height:18px;border-radius:3px;background:{colour};flex-shrink:0"></div>'
        f'<span>{label}</span></div>'
        for label, colour in LEGEND.items()
    )
    return f"""
    <div id="lesion-legend" style="position:fixed;bottom:20px;left:20px;background:rgba(15,23,42,0.92);
         border:1px solid rgba(255,255,255,0.15);border-radius:12px;padding:16px 20px;
         font-family:sans-serif;font-size:13px;color:#e2e8f0;z-index:9999;max-width:320px;transition: all 0.3s ease;">
      <div style="font-weight:700;font-size:15px;margin-bottom:10px;color:#c4b5fd">
        J.B.R. — Lesion Map Legend
      </div>
      {items}
      <div style="margin-top:10px;font-size:11px;color:#64748b">
        MNI152 template · Harvard-Oxford atlas<br>
        Opacity reflects severity (right &gt; left)
      </div>
    </div>"""


def get_mobile_patch():
    """Returns CSS and JS to be injected for mobile friendliness."""
    return """
<style>
    /* Mobile-specific controls */
    #mobile-controls {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(15, 23, 42, 0.95);
        color: white;
        z-index: 10000;
        padding: 15px;
        flex-direction: column;
        gap: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }

    @media (max-width: 768px) {
        #mobile-controls { display: flex; }
        #lesion-legend { 
            transform: scale(0.85); 
            bottom: 10px; 
            left: 10px; 
            max-width: 240px;
            background: rgba(15, 23, 42, 0.8) !important;
        }
        /* Hide nilearn default title/header if it exists */
        .title { display: none !important; }
        
        /* Adjust brain canvas for mobile */
        #view-canvas { margin-top: 100px; }
    }

    .control-row { display: flex; align-items: center; gap: 10px; width: 100%; }
    .btn-group { display: flex; background: #1e293b; border-radius: 8px; padding: 3px; flex: 1; }
    .btn-group button {
        flex: 1;
        background: transparent;
        border: none;
        color: #94a3b8;
        padding: 8px;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    .btn-group button.active {
        background: #6366f1;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    input[type=range] {
        flex: 2;
        accent-color: #6366f1;
    }
    
    .slice-label { min-width: 60px; font-family: monospace; font-size: 14px; text-align: right; }
</style>

<div id="mobile-controls">
    <div class="control-row">
        <div style="font-size: 11px; font-weight: 700; color: #818cf8; text-transform: uppercase;">Orientation</div>
        <div class="btn-group">
            <button onclick="setOrientation('X')" id="btn-X">Sagittal</button>
            <button onclick="setOrientation('Y')" id="btn-Y">Coronal</button>
            <button onclick="setOrientation('Z')" id="btn-Z" class="active">Axial</button>
        </div>
    </div>
    <div class="control-row">
        <div style="font-size: 11px; font-weight: 700; color: #818cf8; text-transform: uppercase;">Slice</div>
        <input type="range" id="slice-slider" min="0" max="100" value="50" oninput="updateBrainSlice(this.value)">
        <span id="slice-val" class="slice-label">#50</span>
    </div>
</div>

<script>
    let currentPlane = 'Z';
    
    function setOrientation(plane) {
        currentPlane = plane;
        ['X', 'Y', 'Z'].forEach(p => {
            const btn = document.getElementById('btn-' + p);
            if (btn) btn.classList.toggle('active', p === plane);
        });
        
        if (window.brain) {
            const max = window.brain.nbSlice[plane] - 1;
            const slider = document.getElementById('slice-slider');
            slider.max = max;
            const currentVal = Math.round(window.brain.numSlice[plane]);
            slider.value = currentVal;
            document.getElementById('slice-val').innerText = '#' + currentVal;
            
            // Trigger redraw
            window.brain.drawAll();
        }
    }

    function updateBrainSlice(val) {
        document.getElementById('slice-val').innerText = '#' + val;
        if (window.brain) {
            window.brain.numSlice[currentPlane] = parseFloat(val);
            window.brain.drawAll();
        }
    }

    // Periodically check for the brain object
    const checkBrain = setInterval(() => {
        if (window.brain) {
            clearInterval(checkBrain);
            setOrientation('Z');
        }
    }, 500);
</script>
"""


def export_volumetric(lesion_img, output_path):
    """Interactive volumetric glass-brain HTML via view_img."""
    print("Generating volumetric interactive view…")
    html_view = plotting.view_img(
        lesion_img,
        bg_img="MNI152",
        threshold=0.5,
        colorbar=False,
        title="J.B.R. Lesion (Harvard-Oxford / MNI152)",
        cmap="hot",
        symmetric_cmap=False,
        vmax=len(LESION_REGIONS),
    )
    # Get direct HTML instead of iframe
    if hasattr(html_view, "as_html"):
        full_html = html_view.as_html()
    else:
        # Fallback for different nilearn versions
        full_html = html_view._repr_html_()

    # 1. Make the 'brain' variable global so we can control it
    full_html = full_html.replace("var brain = brainsprite", "window.brain = brainsprite")
    
    # Also handle the case where it might be inside a srcdoc string
    full_html = full_html.replace("var brain = brainsprite", "window.brain = brainsprite")

    # 2. Inject legend and mobile patch before </body> or </html>
    custom_ui = f"{get_mobile_patch()}\n{make_legend_html()}"
    
    if "</body>" in full_html:
        full_html = full_html.replace("</body>", f"{custom_ui}\n</body>")
    elif "</html>" in full_html:
        full_html = full_html.replace("</html>", f"{custom_ui}\n</html>")
    else:
        full_html += custom_ui

    # 3. Add mobile viewport meta if missing
    if '<meta name="viewport"' not in full_html:
        if "<head>" in full_html:
            full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')
        else:
            # If no head, just prepend it
            full_html = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">' + full_html
    
    # 4. Force background to be dark
    full_html = full_html.replace("body {", "body { background: #0f172a !important; ")

    with open(output_path, "w") as f:
        f.write(full_html)
    print(f"  Saved → {output_path}")


def export_surface(lesion_img, output_path):
    """Interactive inflated surface HTML via view_img_on_surf."""
    print("Generating surface rendering…")
    html_view = plotting.view_img_on_surf(
        lesion_img,
        surf_mesh="fsaverage5",
        threshold=0.5,
        cmap="hot",
        colorbar=False,
        title="J.B.R. Lesion — Cortical Surface (Nilearn)",
        symmetric_cmap=False,
    )
    if hasattr(html_view, "as_html"):
        full_html = html_view.as_html()
    else:
        full_html = html_view._repr_html_()

    # Inject legend
    full_html = full_html.replace("</body>", f"{make_legend_html()}</body>")

    # Add mobile viewport meta
    if '<meta name="viewport"' not in full_html:
        full_html = full_html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1.0">')

    with open(output_path, "w") as f:
        f.write(full_html)
    print(f"  Saved → {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("J.B.R. Brain Lesion Visualiser — Nilearn / MNI152")
    print("=" * 60)

    sub_atlas, cort_atlas = fetch_atlases()

    print("\nBuilding lesion map…")
    lesion_img = build_lesion_map(sub_atlas, cort_atlas)

    print("\nExporting HTML scenes…")
    export_volumetric(
        lesion_img,
        os.path.join(OUTPUT_DIR, "jbr_damage_nilearn.html")
    )
    export_surface(
        lesion_img,
        os.path.join(OUTPUT_DIR, "jbr_surface_nilearn.html")
    )

    print("\n✅ Done! Both files are now available in the Admin Panel.")
    print("   jbr_damage_nilearn.html  — volumetric cross-section viewer")
    print("   jbr_surface_nilearn.html — inflated cortical surface view")
