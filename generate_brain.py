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
from vedo import Plotter, settings as vsettings
import os

def export_custom(scene, output_filename):
    print(f"Exporting interactive 3D scene to {output_filename}...")
    
    # Needs to be rendered to generate labels
    if not scene.is_rendered:
        scene.render(interactive=False)

    # Export customized K3D
    vsettings.default_backend = "k3d"
    plt = Plotter()
    plt.add(scene.clean_renderables).render()
    k_plot = plt.show(interactive=False)

    # Hide grid and menu
    try: k_plot.grid_visible = False
    except: pass
    try: k_plot.menu_visibility = False
    except: pass

    with open(output_filename, "w") as fp:
        fp.write(k_plot.get_snapshot())

    vsettings.default_backend = "vtk"
    print(f"Done! Saved to {output_filename}")


def export_jbr_damage():
    scene = Scene(title="J.B.R.'s Damage (The Anterior Temporal Hub)", inset=False)
    scene.add_brain_region("root", alpha=0.1, color="grey")

    regions = {
        "ENT": "orange",
        "PERI": "red",
        "HIP": "darkred",
        "HPF": "darkred",
        "CA": "darkred",
        "DG": "darkred",
        "AAA": "pink",
        "BLA": "pink",
        "BMA": "pink",
        "CEA": "pink",
        "LA": "pink",
        "MEA": "pink",
        "TEa": "purple",
        "PIR": "yellow",
        "ECT": "brown"
    }
    
    print("Adding J.B.R. damage regions...")
    for acr, color in regions.items():
        try:
            actor = scene.add_brain_region(acr, alpha=0.8, color=color)
            if actor:
                if isinstance(actor, list):
                    actor = actor[0]
                scene.add_label(actor, acr)
        except Exception as e:
            print(f"Could not load region {acr}: {e}")

    export_custom(scene, "jbr_damage.html")


def export_modern_action():
    scene = Scene(title="Occipitotemporal Cortex & Modern Action Networks", inset=False)
    scene.add_brain_region("root", alpha=0.1, color="grey")

    regions = {
        "VISl": "blue",
        "VISal": "blue",
        "VISpl": "blue",
        "VISpor": "cyan",
        "PTLp": "green",
        "TEa": "purple",
        "MOs": "red",
        "RSP": "orange"
    }

    print("Adding modern action regions...")
    for acr, color in regions.items():
        try:
            actor = scene.add_brain_region(acr, alpha=0.8, color=color)
            if actor:
                if isinstance(actor, list):
                    actor = actor[0]
                scene.add_label(actor, acr)
        except Exception as e:
            print(f"Could not load region {acr}: {e}")

    export_custom(scene, "modern_action.html")


if __name__ == "__main__":
    print("Initialising brainrender scenes...")
    export_jbr_damage()
    export_modern_action()
