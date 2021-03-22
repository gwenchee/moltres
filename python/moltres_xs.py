#!/usr/bin/env python3
# This script extracts homogenized group constants from Serpent 2 or SCALE 
# or OpenMC into a JSON data file to be used with MoltresJsonMaterial.
import json
import sys
import argparse
import numpy as np
import importlib
import openmc
import openmc.mgxs as mgxs


class openmc_xs:
    def __init__(self, xs_filename, xs_ref_filename, file_num):
        sp = openmc.StatePoint(xs_filename)
        domain_dict = openmc_ref_modules[file_num].domain_dict
        num_burn = 1 
        num_uni = []
        for k in sp.filters: 
            v = sp.filters[k]
            if isinstance(v, openmc.filter.CellFilter):
                num_uni.append(v.bins[0])
        num_temps = 1
        self.xs_lib = {}
        for i in range(num_burn):
            self.xs_lib[i] = {}
            for j in num_uni:
                self.xs_lib[i][j-1] = {}
                for k in range(num_temps):
                    self.xs_lib[i][j-1][k] = {}
                    self.xs_lib[i][j-1][k]["FISSXS"] = self.get_tallies_list(sp, domain_dict[j]["fissionxs"])

    def get_tallies_list(self, sp, tally):
        tally.load_from_statepoint(sp)
        return list(tally.get_pandas_dataframe()["mean"])


    def generate_openmc_tallies_xml(
        energy_groups, delayed_groups, domains, domain_ids, tallies_file
    ):
        groups = mgxs.EnergyGroups()
        groups.group_edges = np.array(energy_groups)
        big_group = mgxs.EnergyGroups()
        big_energy_group = [energy_groups[0], energy_groups[-1]]
        big_group.group_edges = np.array(big_energy_group)
        energy_filter = openmc.EnergyFilter(energy_groups)
        domain_dict = {}
        for id in domain_ids:
            domain_dict[id] = {}
        for domain, id in zip(domains, domain_ids):
            domain_dict[id]["beta"] = mgxs.Beta(
                domain=domain,
                energy_groups=big_group,
                delayed_groups=delayed_groups,
                name=str(id) + "_beta",
            )
            domain_dict[id]["chi"] = mgxs.Chi(
                domain=domain, groups=groups, name=str(id) + "_chi"
            )
            domain_dict[id]["chidelayed"] = mgxs.ChiDelayed(
                domain=domain, energy_groups=groups, name=str(id) + "_chidelayed"
            )
            domain_dict[id]["decayrate"] = mgxs.DecayRate(
                domain=domain,
                energy_groups=big_group,
                delayed_groups=delayed_groups,
                name=str(id) + "_decayrate",
            )
            domain_dict[id]["scatterprobmatrix"] = mgxs.ScatterProbabilityMatrix(
                domain=domain, groups=groups, name=str(id) + "_scatterprobmatrix"
            )
            domain_dict[id]["inversevelocity"] = mgxs.InverseVelocity(
                domain=domain, groups=groups, name=str(id) + "_inversevelocity"
            )
            domain_dict[id]["fissionxs"] = mgxs.FissionXS(
                domain=domain, groups=groups, name=str(id) + "_fissionxs"
            )
            domain_dict[id]["tally"] = openmc.Tally(name=str(id) + " tally")
            domain_dict[id]["filter"] = openmc.CellFilter(domain)
            domain_dict[id]["tally"].filters = [
                domain_dict[id]["filter"],
                energy_filter,
            ]
            domain_dict[id]["tally"].scores = [
                "kappa-fission",
                "nu-fission",
                "absorption",
                "scatter",
            ]
            tallies_file += domain_dict[id]["beta"].tallies.values()
            tallies_file += domain_dict[id]["chi"].tallies.values()
            tallies_file += domain_dict[id]["chidelayed"].tallies.values()
            tallies_file += domain_dict[id]["decayrate"].tallies.values()
            tallies_file += domain_dict[id]["scatterprobmatrix"].tallies.values()
            tallies_file += domain_dict[id]["inversevelocity"].tallies.values()
            tallies_file += domain_dict[id]["fissionxs"].tallies.values()
            tallies_file.append(domain_dict[id]["tally"])
        tallies_file.export_to_xml()
        return domain_dict


class scale_xs:
    """
        Python class that reads in a scale t16 file and organizes the cross
        section data into a numpy dictionary. Currently set up to read an
        arbitrary number of energy groups, an arbitrary number of delayed
        neutron groups, an arbitrary number of identities, an arbitrary
        number of temperature branches, and an arbitrary number of burnups.

        Parameters
        ----------
        xs_filename: str
            Name of file containing collapsed cross section data
        Returns
        ----------
        xs_lib: dict
            A hierarchical dictionary, organized by burnup, id,
            and temperature.
            Currently stores REMXS, FISSXS, NSF, FISSE, DIFFCOEF, RECIPVEL,
            CHI, BETA_EFF, DECAY_CONSTANT and GTRANSFXS.
    """

    def __init__(self, xs_filename):
        with open(xs_filename) as f:
            self.lines = f.readlines()
        self.catch = {
            'Betas': self.t16_line([], True, ['BETA_EFF']),
            'Lambdas': self.t16_line([], True, ['DECAY_CONSTANT']),
            'total-transfer': self.t16_line([1], False, ['REMXS']),
            'fission': self.t16_line([0, 3, 4], False,
                                     ['FISSXS', 'NSF', 'FISSE']
                                     ),
            'chi': self.t16_line([1, 1, 1, 2], False,
                                 ['CHI_T', 'CHI_P', 'CHI_D', 'DIFFCOEF']
                                 ),
            'detector': self.t16_line([4], False, ['RECIPVEL']),
            'Scattering cross': self.t16_line([], True, ['GTRANSFXS'])
            }
        XS_entries = ['REMXS', 'FISSXS', 'NSF', 'FISSE', 'DIFFCOEF',
                      'RECIPVEL', 'CHI_T', 'BETA_EFF', 'DECAY_CONSTANT',
                      'CHI_P', 'CHI_D', 'GTRANSFXS'
                      ]
        struct = (self.lines[3].split()[:4])
        self.num_burn = int(struct[0])
        self.num_temps = int(struct[1]) + 1
        self.num_uni = int(struct[2])
        self.num_groups = int(struct[3])
        self.xs_lib = {}
        for i in range(self.num_burn):
            self.xs_lib[i] = {}
            for j in range(self.num_uni):
                self.xs_lib[i][j] = {}
                for k in range(self.num_temps):
                    self.xs_lib[i][j][k] = {}
                    for entry in XS_entries:
                        self.xs_lib[i][j][k][entry] = []
        self.get_xs()
        self.fix_xs()

    class t16_line:
        def __init__(self, ind, multi, entry):
            self.index = ind
            self.multi_line_flag = multi
            self.xs_entry = entry

    def fix_xs(self):
        for i in range(self.num_burn):
            for j in range(self.num_uni):
                for k in range(self.num_temps):
                    for ii in range(self.num_groups):
                        start = ii*self.num_groups
                        stop = start + self.num_groups
                        self.xs_lib[i][j][k]["REMXS"][ii] += np.sum(
                            self.xs_lib[i][j][k]["GTRANSFXS"][start:stop])\
                            - self.xs_lib[i][j][k]["GTRANSFXS"][start+ii]
                        if self.xs_lib[i][j][k]["FISSE"][ii] != 0:
                            self.xs_lib[i][j][k]["FISSE"][ii] = (
                                self.xs_lib[i][j][k]["FISSE"][ii] /
                                self.xs_lib[i][j][k]["FISSXS"][ii]
                                )

    def get_xs(self):
        uni = []
        L = 0
        m = 0
        n = 0
        lam_temp = 0
        beta_temp = 0
        for k, line in enumerate(self.lines):
            if 'Identifier' in line:
                val = int(self.lines[k+1].split()[0])
                if val not in uni:
                    uni.extend([val])
                m = uni.index(val)
                self.xs_lib[L][m][n]['BETA_EFF']\
                    .extend(beta_temp)
                self.xs_lib[L][m][n]['DECAY_CONSTANT']\
                    .extend(lam_temp)
            if 'branch no.' in line:
                index = line.find(',')
                L = int(line[index-4:index])
                n = int(line.split()[-1])
            for key in self.catch.keys():
                if key in line:
                    if self.catch[key].multi_line_flag:
                        if (key == 'Betas'):
                            beta_temp = self.get_multi_line_values(k)
                        elif(key == 'Lambdas'):
                            lam_temp = self.get_multi_line_values(k)
                        else:
                            self.xs_lib[L][m][n][self.catch[key].xs_entry[0]]\
                                .extend(
                                    self.get_multi_line_values(k)
                                    )
                    else:
                        for dex, xs in enumerate(self.catch[key].xs_entry):
                            dex = self.catch[key].index[dex]
                            self.xs_lib[L][m][n][xs]\
                                .append(self.get_values(k, dex))

    def get_values(self, k, index):
        val = list(np.array(self.lines[k+1].split()).astype(float))
        return val[index]

    def get_multi_line_values(self, k):
        values = []
        while True:
            val = self.lines[k+1].split()
            k += 1
            for ent in val:
                try:
                    values.append(float(ent))
                except(ValueError):
                    return values


class serpent_xs:
    """
        Python class that reads in a serpent res file and organizes the cross
        section data into a numpy dictionary. Currently set up to read an
        arbitrary number of energy groups, delayed neutron groups, identities,
        temperature branches, and burnups.

        Parameters
        ----------
        xs_filename: str
            Name of file containing collapsed cross section data
        Returns
        ----------
        xs_lib: dict
            A hierarchical dict, organized by burnup, id, and temperature.
            Stores REMXS, FISSXS, NSF, FISSE, DIFFCOEF, RECIPVEL, CHI,
            BETA_EFF, DECAY_CONSTANT and GTRANSFXS.
    """

    def __init__(self, xs_filename):
        data = serpent.parse_res(xs_filename)
        try:
            num_burn = len(np.unique(data['BURNUP'][:][0]))
        except(KeyError):
            num_burn = 1
        num_uni = len(np.unique(data['GC_UNIVERSE_NAME']))
        num_temps = int(len(data['GC_UNIVERSE_NAME'])/(num_uni*num_burn))
        self.xs_lib = {}
        for i in range(num_burn):
            self.xs_lib[i] = {}
            for j in range(num_uni):
                self.xs_lib[i][j] = {}
                for k in range(num_temps):
                    self.xs_lib[i][j][k] = {}
                    index = i*(num_uni)+k*(num_burn*num_uni)+j
                    self.xs_lib[i][j][k]["REMXS"] = list(
                        data['INF_REMXS'][index][::2])
                    self.xs_lib[i][j][k]["FISSXS"] = list(
                        data['INF_FISS'][index][::2])
                    self.xs_lib[i][j][k]["NSF"] = list(
                        data['INF_NSF'][index][::2])
                    self.xs_lib[i][j][k]["FISSE"] = list(
                        data['INF_KAPPA'][index][::2])
                    self.xs_lib[i][j][k]["DIFFCOEF"] = list(
                        data['INF_DIFFCOEF'][index][::2])
                    self.xs_lib[i][j][k]["RECIPVEL"] = list(
                        data['INF_INVV'][index][::2])
                    self.xs_lib[i][j][k]["CHI_T"] = list(
                        data['INF_CHIT'][index][::2])
                    self.xs_lib[i][j][k]["CHI_P"] = list(
                        data['INF_CHIP'][index][::2])
                    self.xs_lib[i][j][k]["CHI_D"] = list(
                        data['INF_CHID'][index][::2])
                    self.xs_lib[i][j][k]["BETA_EFF"] = list(
                        data['BETA_EFF'][index][2::2])
                    self.xs_lib[i][j][k]["DECAY_CONSTANT"] = list(
                        data['LAMBDA'][index][2::2])
                    self.xs_lib[i][j][k]["GTRANSFXS"] = list(
                        data['INF_SP0'][index][::2])


def read_input(fin):
    with open(fin) as f:
        lines = f.readlines()
    k = 0
    for k, line in enumerate(lines):
        if '[TITLE]' in line:
            f = open(lines[k+1].split()[0], 'w')
        if '[MAT]' in line:
            mat_dict = {}
            num_mats = int(lines[k+1].split()[0])
            val = lines[k+2].split()
            for i in range(num_mats):
                mat_dict[val[i]] = {'temps': [],
                                    'file': [],
                                    'uni': [],
                                    'burn': [],
                                    'bran': []
                                    }
        if '[BRANCH]' in line:
            tot_branch = int(lines[k+1].split()[0])
            for i in range(tot_branch):
                val = lines[k+2+i].split()
                mat_dict[val[0]]['temps'].extend(
                    [int(val[1])])
                mat_dict[val[0]]['file'].extend(
                    [int(val[2])])
                mat_dict[val[0]]['burn'].extend(
                    [int(val[3])])
                mat_dict[val[0]]['uni'].extend(
                    [int(val[4])])
                mat_dict[val[0]]['bran'].extend(
                    [int(val[5])])

        if 'FILES' in line:
            num_files = int(lines[k+1].split()[0])
            files = {}
            for i in range(num_files):
                try:
                    XS_in, XS_t, XS_ref = lines[k+2+i].split()
                except: 
                    XS_in, XS_t = lines[k+2+i].split()
                if 'scale' in XS_t:
                    files[i] = scale_xs(XS_in)
                elif 'serpent' in XS_t:
                    files[i] = serpent_xs(XS_in)
                elif 'openmc' in XS_t:
                    files[i] = openmc_xs(XS_in, XS_ref, i+1)
                else:
                    raise("XS data not understood\n \
                          Please use: scale, serpent, or openmc.")
    print("mat dict",mat_dict)
    out_dict = {}
    for mat in mat_dict:
        out_dict[mat] = {'temp': mat_dict[mat]['temps']}
        for i, temp in enumerate(mat_dict[mat]['temps']):
            # change to index by zero 
            file_index = mat_dict[mat]['file'][i] - 1
            burnup_index = mat_dict[mat]['burn'][i] - 1
            uni_index = mat_dict[mat]['uni'][i] - 1
            branch_index = mat_dict[mat]['bran'][i] - 1
            out_dict[mat][str(temp)] = files[file_index].xs_lib[burnup_index][uni_index][branch_index]
    f.write(json.dumps(out_dict, sort_keys=True, indent=4))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Extracts Serpent 2 or SCALE group \
            constants and puts them in a JSON file suitable \
                for Moltres.')
    parser.add_argument('input_file', type=str,
                        nargs=1, help='*_res.m or *.t16 XS \
                            file from Serpent 2 or SCALE, \
                            respectively')
    args = parser.parse_args()
    # import relevant modules for each software
    with open(sys.argv[1]) as f:
        lines = f.readlines()
        k = 0
        for k, line in enumerate(lines):
            if 'FILES' in line:
                num_files = int(lines[k+1].split()[0])
                files = {}
                for i in range(num_files):
                    try:
                        XS_in, XS_t, XS_ref = lines[k+2+i].split()
                    except: 
                        XS_in, XS_t = lines[k+2+i].split()
                    if 'openmc' in XS_t:
                        openmc_ref_modules = {} 
                        openmc_ref_modules[i+1] = importlib.import_module(XS_ref.replace(".py", ""))
                    elif 'serpent' in XS_t:
                        from pyne import serpent

    read_input(sys.argv[1])

    print("Successfully made JSON property file.")
