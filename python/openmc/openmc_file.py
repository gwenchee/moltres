import sys
sys.path.insert(1, '../')
from moltres_xs import *
import openmc

uoc_9 = openmc.Material()
uoc_9.set_density("atom/b-cm", 7.038386e-2)
uoc_9.add_nuclide("U235", 2.27325e-3)
uoc_9.add_nuclide("U238", 2.269476e-2)
uoc_9.add_nuclide("O16", 3.561871e-2)
uoc_9.add_nuclide("C0", 9.79714e-3)
uoc_9.temperature = 900

graphite = openmc.Material()
graphite.set_density("g/cc", 1.8)
graphite.add_nuclide("C0", 9.025164e-2)
graphite.temperature = 900

mats = openmc.Materials([uoc_9, graphite])
mats.export_to_xml()

sphere = openmc.Sphere(r=6.3849)
fuel = openmc.Cell(fill=uoc_9, region=-sphere, cell_id=1)
outer_sphere = openmc.Sphere(r=8, boundary_type="reflective")
moderator = openmc.Cell(fill=graphite, region=+sphere & -outer_sphere, cell_id=2)
geom = openmc.Geometry([fuel, moderator])
geom.export_to_xml()

settings = openmc.Settings()
settings.batches = 50
settings.inactive = 10
settings.particles = 5000
settings.temperature = {"multipole": True, "method": "interpolation"}
settings.export_to_xml()

tallies_file = openmc.Tallies()
domain_dict = openmc_xs.generate_openmc_tallies_xml(
    [1e-8, 1, 1e3, 1e5, 20.0e7],
    list(range(1, 7)),
    [fuel, moderator],
    [fuel.id, moderator.id],
    tallies_file,
)

