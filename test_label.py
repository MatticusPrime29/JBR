from brainrender import Scene
from vedo import Plotter, settings as vsettings
from pathlib import Path

def test_label():
    scene = Scene(title="Test", inset=False)
    actor = scene.add_brain_region("TEa", alpha=0.8, color="red")
    if isinstance(actor, list): actor = actor[0]
    
    scene.add_label(actor, "TEa")
    
    # render
    if not scene.is_rendered:
        scene.render(interactive=False)

    # Export customized K3D
    vsettings.default_backend = "k3d"
    plt = Plotter()
    plt.add(scene.clean_renderables).render()
    k_plot = plt.show(interactive=False)
    
    # Hide axes and menu
    try: k_plot.grid_visible = False
    except: pass
    try: k_plot.menu_visibility = False
    except: pass
    
    with open("test_label.html", "w") as fp:
        fp.write(k_plot.get_snapshot())

if __name__ == "__main__":
    test_label()
