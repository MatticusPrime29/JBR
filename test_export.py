from brainrender import Scene
from vedo import Plotter, settings as vsettings

# 1. Create scene
scene = Scene(title="Test", inset=False)
scene.add_brain_region("TEa", alpha=0.8, color="red")

# 2. Add text overlays / labels. K3D supports text?
# Brainrender's Text2D doesn't export to K3D. 
# vedo texts: vedo.Text3D ?
import vedo

text = vedo.Text3D("This is a label", pos=(1000, 1000, 1000), s=200, c="black")
scene.add(text)

# 3. Export custom
vsettings.default_backend = "k3d"
plt = Plotter(axes=False)
plt.add(scene.clean_renderables).render()

k_plot = plt.show(interactive=False)

# k_plot should be a k3d Plot object
try:
    k_plot.axes = []
except Exception as e:
    print("could not remove axes", e)

try:
    k_plot.grid_visible = False
except Exception as e:
    print("could not set grid_visible", e)
    
try:
    k_plot.menu_visibility = False
except Exception as e:
    print("could not hide menu", e)

with open("test_custom_export.html", "w") as fp:
    fp.write(k_plot.get_snapshot())

print("Test exported")
