import openmc

# Create plutonium metal material
pu = openmc.Material()
pu.set_density("sum")
pu.add_nuclide("Pu239", 3.7047e-02)
pu.add_nuclide("Pu240", 1.7512e-03)
pu.add_nuclide("Pu241", 1.1674e-04)
pu.add_element("Ga", 1.3752e-03)
pu.temperature = 900

graphite = openmc.Material()
graphite.set_density("g/cc", 1.8)
graphite.add_nuclide("C0", 9.025164e-2)
graphite.temperature = 900

mats = openmc.Materials([pu, graphite])
mats.export_to_xml()

# Create a single cell filled with the Pu metal
sphere = openmc.Sphere(r=6.3849)
cell = openmc.Cell(fill=pu, region=-sphere)
outer_sphere = openmc.Sphere(r=8, boundary_type="vacuum")
outer_cell = openmc.Cell(fill=graphite, region=+sphere & -outer_sphere)
geom = openmc.Geometry([cell, outer_cell])
geom.export_to_xml()

# Finally, define some run settings
settings = openmc.Settings()
settings.batches = 200
settings.inactive = 10
settings.particles = 10000
settings.temperature = {"multipole": True, "method": "interpolation"}
settings.export_to_xml()

# plot
plot = openmc.Plot()
plot.basis = "xy"
plot.origin = (0, 0, 0)
plot.width = (20, 20)
plot.pixels = (200, 200)
colors = {
    graphite: "grey",
    pu: "blue",
}
plot.color_by = "material"
plot.colors = colors
plots = openmc.Plots()
plots.append(plot)
plots.export_to_xml()

tallies_file = openmc.Tallies()
# beta
energy_filter = openmc.EnergyFilter([1e-8, 20.0e7])
mesh = openmc.RegularMesh(mesh_id=1)
mesh.dimension = [1, 1]
mesh.lower_left = [-10.0, -10.0]
mesh.upper_right = [10.0, 10.0]
mesh_filter = openmc.MeshFilter(mesh)
tally = openmc.Tally(name="mesh tally")
tally.filters = [mesh_filter, energy_filter]
tally.scores = [
    "delayed-nu-fission",
    "nu-fission",
    "decay-rate",
    "kappa-fission",
    "inverse-velocity",
    "absorption", 
    "scatter", 
    "fission"
]
tallies_file.append(tally)
tallies_file.export_to_xml()
