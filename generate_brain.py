"""
generate_brain.py - Prototype Python script to export interactive Brainrender scenes.

REQUIREMENTS:
pip install brainrender

USAGE:
Run this script locally on your Windows machine to generate the 3D HTML files.
These files will be saved in this directory and become immediately available
in your Admin Control Panel to push to the students.
"""

from brainrender import Scene
from brainrender.actors import Volume
import os

print("Initialising brainrender scene...")

def export_jbr_lesion():
    # 1. Create a scene
    scene = Scene(title="J.B.R. Bilateral Temporal Lesion", inset=False)
    
    # 2. Add the whole brain outline (glass brain)
    scene.add_brain_region("root", alpha=0.1, color="grey")
    
    # 3. Add explicit neuroanatomical regions to represent the lesions
    # J.B.R. had bilateral temporal lobe damage. We can use the Allen Brain Atlas acronyms.
    # We will highlight the TEa (Temporal area) and VISC (Visceral area) or general temporal regions.
    # For a general representation, we can highlight the hippocampus (HIP) and amygdala (MEA/CEA) and temporal poles.
    
    print("Adding temporal lobe regions...")
    try:
        # Highlight regions often involved in severe semantic visual agnosia/Herpes Simplex Encephalitis
        # 'TEa' = Temporal area, 'PERI' = Perirhinal area, 'ENT' = Entorhinal area
        scene.add_brain_region("TEa", alpha=0.8, color="red")     # Temporal Area
        scene.add_brain_region("ENT", alpha=0.8, color="orange")  # Entorhinal area
        scene.add_brain_region("PERI", alpha=0.8, color="red")    # Perirhinal area
        scene.add_brain_region("HIP", alpha=0.8, color="darkred") # Hippocampal region
    except Exception as e:
        print(f"Could not load all specific regions: {e}")

    # 4. Export the scene to HTML
    output_filename = "jbr_lesion.html"
    print(f"Exporting interactive 3D scene to {output_filename}...")
    
    # Brainrender uses K3D under the hood to export html
    # The export function saves it to the current working directory.
    scene.export(output_filename)
    print("Done! You can now select this file in your Admin Panel.")


if __name__ == "__main__":
    export_jbr_lesion()
