import openmc
import openmc.mgxs as mgxs
import numpy as np

# Create plutonium metal material
pu = openmc.Material()
pu.set_density("sum")
pu.add_nuclide("Pu239", 3.7047e-02)
pu.add_nuclide("Pu240", 1.7512e-03)
pu.add_nuclide("Pu241", 1.1674e-04)
pu.add_element("Ga", 1.3752e-03)
pu.temperature = 900

uoc_9 = openmc.Material()
uoc_9.set_density('atom/b-cm', 7.038386E-2)
uoc_9.add_nuclide('U235', 2.27325e-3)
uoc_9.add_nuclide('U238', 2.269476e-2)
uoc_9.add_nuclide('O16', 3.561871e-2)
uoc_9.add_nuclide('C0', 9.79714e-3)
uoc_9.temperature = 900

graphite = openmc.Material()
graphite.set_density("g/cc", 1.8)
graphite.add_nuclide("C0", 9.025164e-2)
graphite.temperature = 900

mats = openmc.Materials([uoc_9, graphite])
mats.export_to_xml()

# Create a single cell filled with the fuel
sphere = openmc.Sphere(r=6.3849)
fuel = openmc.Cell(fill=uoc_9, region=-sphere)
outer_sphere = openmc.Sphere(r=8, boundary_type="reflective")
moderator = openmc.Cell(fill=graphite, region=+sphere & -outer_sphere)
geom = openmc.Geometry([fuel, moderator])
geom.export_to_xml()

# Finally, define some run settings
settings = openmc.Settings()
settings.batches = 50
settings.inactive = 10
settings.particles = 5000
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
    uoc_9: "blue",
}
plot.color_by = "material"
plot.colors = colors
plots = openmc.Plots()
plots.append(plot)
plots.export_to_xml()

tallies_file = openmc.Tallies()
# beta
energy_filter = openmc.EnergyFilter([1e-8, 1, 1e4, 20.0e7])
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
#tallies_file.append(tally)

# mgxs 
groups = mgxs.EnergyGroups()
groups.group_edges = np.array([1.0e-8, 1.0, 1.0e4, 20.0e7])
fuel_beta = mgxs.Beta(domain=fuel, energy_groups=groups)
fuel_chi = mgxs.Chi(domain=fuel, groups=groups)
moderator_chi = mgxs.Chi(domain=moderator, groups=groups)
fuel_chidelayed = mgxs.ChiDelayed(domain=fuel, energy_groups=groups)
moderator_chidelayed = mgxs.ChiDelayed(domain=moderator, energy_groups=groups)
fuel_decayrate = mgxs.DecayRate(domain=fuel, energy_groups=groups)
fuel_spm = mgxs.ScatterProbabilityMatrix(domain=fuel, groups=groups)
moderator_spm = mgxs.ScatterProbabilityMatrix(domain=moderator, groups=groups)
fuel_trxs = mgxs.TransportXS(domain=fuel, groups=groups)
moderator_trxs = mgxs.TransportXS(domain=moderator, groups=groups)
fuel_kfxs = mgxs.KappaFissionXS(domain=fuel, groups=groups)
fuel_nfmxs = mgxs.NuFissionMatrixXS(domain=fuel, groups=groups)
fuel_fxs = mgxs.FissionXS(domain=fuel, groups=groups)
fuel_iv = mgxs.InverseVelocity(domain=fuel, groups=groups)

tallies_file += fuel_beta.tallies.values()
tallies_file += fuel_chi.tallies.values()
tallies_file += moderator_chi.tallies.values()
tallies_file += fuel_chidelayed.tallies.values()
tallies_file += moderator_chidelayed.tallies.values()
tallies_file += fuel_decayrate.tallies.values()
tallies_file += fuel_spm.tallies.values()
tallies_file += moderator_spm.tallies.values()
tallies_file += fuel_trxs.tallies.values()
tallies_file += moderator_trxs.tallies.values()
tallies_file += fuel_kfxs.tallies.values()
tallies_file += fuel_nfmxs.tallies.values()
tallies_file += fuel_fxs.tallies.values()
tallies_file += fuel_iv.tallies.values()
tallies_file.export_to_xml()

openmc.run()

sp = openmc.StatePoint('statepoint.50.h5')
fuel_beta.load_from_statepoint(sp)
fuel_beta.get_pandas_dataframe()
fuel_beta.print_xs()