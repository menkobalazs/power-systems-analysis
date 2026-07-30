################
### Packages ###
################

import re
import json
import hashlib
import pypsa
import numpy as np
import pandas as pd
from glob import glob
from pathlib import Path
from scipy.stats import qmc
np.random.seed(42) # fix random seed for reproducibility

####################################
### Constants and Configurations ###
####################################

data_path = 'data/' + 'Adatok_HU_2050.xlsx'
cost_params = ['capital', 'environment', 'operation', 'reliability', 'risk']
week_numbers =  {'week_15':15, 'week_28':28, 'week_40':40, 'week_49':49}
seasons = {'Spring': 1, 'Summer': 2, 'Autumn': 3, 'Winter': 4}
tech_colors = {
    # Generators
    'Solar': '#FFD700',            # Bright Gold/Yellow
    'Wind Offshore': '#00E5FF',    # Electric Cyan
    'Wind Onshore': '#00C853',     # High-contrast Vivid Green
    'Hydro Run-of-river': '#2979FF', # Vivid Azure Blue
    'Hydro Water Reservoir': '#311B92', # Deep Midnight Purple
    'Geothermal': "#FF8800",       # Bright Red-Orange
    'Biomass': '#795548',          # Earthy Walnut Brown
    'Waste': '#C6FF00',            # Acid Lime 
    'Fossil Lignite': '#546E7A',   # Blue-Gray/Slate
    'Fossil Hard coal': '#212121', # Deep Charcoal/Black
    'Fossil Gas': '#B0BEC5',       # Pale Silver
    'Nuclear': '#D500F9',          # Electric Magenta/Purple
    'Fusion': '#F50057',           # Vivid Pink/Deep Rose
    # Storages:
    'Pumped Storage Actual':'#0000FF',
    'Storage Actual ':'#FF0000', # Due to a typo a version exists with a space at the end
    'Storage Actual':'#FF0000'
}

######################################
### Network Optimizations Function ###
######################################

def build_and_optimize_network(name, generator_costs, storage_costs, dates, demand, potentials_generator, potentials_storage, profile_PV, profile_wind, save_path, save_meta_data={}):
    """
    Build and optimize a PyPSA network with given generators, storage units, and demand profile.

    Parameters:
    - name: str, name for the network.
    - generator_costs: dict, cost parameters for each generator technology.
    - storage_costs: dict, cost parameters for each storage technology.
    - dates: list of lists, snapshot timestamps for each season.
    - demand: array-like, residential demand time series.
    - potentials_generator: DataFrame, generator potential constraints (p_nom, p_nom_max, p_nom_min, ramp_up, ramp_down).
    - potentials_storage: DataFrame, storage potential constraints (p_nom_max).
    - profile_PV: DataFrame, solar generation profile.
    - profile_wind: DataFrame, wind generation profile.
    - save_path: str, directory path to save the optimized network as NetCDF.
    - save_meta_data: dict, save key-value pairs in network.meta dictionary.
    Returns:
    - network: pypsa.Network, the optimized network object.
    """
    network = pypsa.Network(name=name)
    snapshots = np.array([item for sublist in dates for item in sublist])
    network.set_snapshots(list(snapshots))
    
    network.add("Bus", "country_0", carrier='AC')
    network.add('Carrier', 'AC')
    network.add("Load", "Residential demand", bus="country_0", p_set=demand)  
    
    network.meta['costs_generator'] = generator_costs
    network.meta['costs_storage'] = storage_costs 
    for key, val in save_meta_data.items():
        network.meta[key] = val

    # Add generators
    for technology in potentials_generator.keys(): 
        p_max_pu, p_min_pu = 1, 0
        if technology == 'Solar':
            p_max_pu = np.repeat(profile_PV.values, 7, axis=1).flatten('F')
        elif technology == 'Wind Onshore':
            p_max_pu = np.repeat(profile_wind.values, 7, axis=1).flatten('F')
        
        network.add(
            "Generator", name=str(technology), bus="country_0",
            p_nom=potentials_generator.loc['p_nom'][str(technology)],
            p_nom_extendable=True,
            p_nom_max=potentials_generator.loc['p_nom_max'][str(technology)],
            p_nom_min=potentials_generator.loc['p_nom_min'][str(technology)],
            capital_cost=generator_costs[str(technology)]['capital'],
            marginal_cost=sum([generator_costs[str(technology)][key] for key in cost_params[1:]]),
            p_max_pu=p_max_pu, p_min_pu=p_min_pu,
            ramp_limit_up=potentials_generator.loc['ramp_up'][str(technology)],
            ramp_limit_down=potentials_generator.loc['ramp_down'][str(technology)]
        )

    # Add storage
    for technology in potentials_storage.keys():
        network.add(
            "StorageUnit", name=str(technology), bus="country_0",
            p_nom_extendable=True,
            p_nom_max=potentials_storage.loc['p_nom_max'][str(technology)],
            capital_cost=storage_costs[str(technology)]['capital'],
            marginal_cost=sum([storage_costs[str(technology)][key] for key in cost_params[1:]]),
        )

    network.sanitize()
    network.meta['simulation_status'] = network.optimize(
        include_objective_constant=False,
        solver_name='highs', log_to_console=False,
        solver_options={'presolve': 'on', 'threads': 'all', 'solver': 'simplex'}
    )
    
    network.export_to_netcdf(f"{save_path}{network.name}.nc")
        
    return network

###################################
### Data Manipulation Functions ###
###################################

def change_costs(costs, technologies=[], cost_params=cost_params, allow_rand_seed=True, function=lambda *args, **kwargs: 1, *args, **kwargs):
    """
    Change the costs of specified technology parameters by applying a given function to them. 
    Parameters:
    - costs: dict, the original costs dictionary to be modified in-place.
    - technologies: list of str, the technologies to modify. If empty, all technologies will be modified.
    - cost_params: list of str, the cost parameters to modify (e.g  'capital', 'operation', etc.).
    - function: callable, a function that takes the original cost value and returns a modified cost value.
      It can also take additional arguments and keyword arguments for more complex modifications.
    - *args, **kwargs: additional arguments and keyword arguments to be passed to the function. 
    """
    if allow_rand_seed: np.random.seed(42) # fix random seed for reproducibility
    if function == 'uniform':
        function = np.random.uniform
    elif function == 'linear':
        function = np.linspace
    elif function == 'constant':
        function = lambda x:x
    # elif function == ...   ### Todo: add more predefined functions if needed
    if not technologies:
        technologies = costs.keys()
    for k in technologies:
        for p in cost_params:
            costs[k][p] = function(*args, **kwargs) * costs[k][p] if type(costs[k][p]) == float else costs[k][p]
    return None

def change_generator_p_nom_max(seed=137, number_of_powerplant=[2,3,4,4]):
    """
    Change the maximum potential of generators for each technology by generating random values.
    Parameters:
    - seed: int, the random seed for reproducibility.
    - number_of_powerplant: list of int, the number of power plants for each technology
      (e.g. [2,3,4,4] means 2 small, 3 medium, 4 large, and 4 with no potential).
      The list will be shuffled randomly to assign the number of power plants to different technologies in a random order.
    Returns:
    - np.array, the new maximum potentials for each generator technology, shuffled randomly.
    """
    np.random.seed(seed)
    # Maximum potential for each technology, generated randomly for demonstration
    number_of_powerplant = np.random.permutation(number_of_powerplant)
    small = np.random.randint(1, 10, number_of_powerplant[0]) * 10 
    medium = np.random.randint(1, 10, number_of_powerplant[1]) * 100
    large = np.random.randint(10, 25, number_of_powerplant[2]) * 100
    combined = small.tolist() + medium.tolist() + large.tolist()
    combined.extend([0] * number_of_powerplant[3])  # Add zeros for technologies with no potential
    return np.array(combined)[np.random.permutation(sum(number_of_powerplant))]

def change_storage_p_nom_max(seed, min=100, max=3000):
    """
    Change the maximum potential of storage units by generating random values.
    Parameters:
    - seed: int, the random seed for reproducibility.
    - min: int, the minimum potential for storage units.
    - max: int, the maximum potential for storage units.
    Returns:
    - np.array, the new maximum potentials for storage units, generated randomly between min and max.
    """
    np.random.seed(seed)
    return np.random.randint(min, max , 2)

######################################
### Functions for Sensitivity Test ###
######################################

def float_sort_key(path):
    """
    Extract a float value from a filename's stem for sorting purposes.

    Parameters:
    - path: str or Path, file path whose stem contains a numeric value.

    Returns:
    - float, the first numeric value found in the stem.
    """
    match = re.search(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', Path(path).stem)
    if match:
        return float(match.group(0))
    raise ValueError(f"No numeric parameter found in filename: {path}")

def read_nc_data(path, baseline):
    """
    Read optimized network results from NetCDF files and compute absolute and normalized capacities.

    Parameters:
    - path: str, glob pattern matching the NetCDF files to read.
    - baseline: pypsa.Network, baseline network whose capacities are subtracted for normalization.

    Returns:
    - tuple of pd.DataFrame: (absolute_capacities, normalized_capacities) where normalized = absolute - baseline.
    """
    nws = {}
    nws_normed = {}
    for file in sorted(glob(path), key=float_sort_key):
        nw = pypsa.Network(file)
        nw_name = nw.name.split('_')
        max_capacities = pd.concat((nw.generators.p_nom_opt.abs(), nw.storage_units.p_nom_opt.abs()))
        nws[nw_name[1]] = np.round(max_capacities, 3)
        nws_normed[nw_name[1]] = max_capacities - pd.concat((baseline.generators.p_nom_opt.abs(), baseline.storage_units.p_nom_opt.abs()))
    return pd.DataFrame(nws), pd.DataFrame(nws_normed)

def calc_diff(data, min_diff=10):
    """
    Compute differences between consecutive columns and identify the range where changes occur.

    Parameters:
    - data: pd.DataFrame, data with numeric columns to differentiate.
    - min_diff: float, minimum difference between numeric columns

    Returns:
    - tuple: (differences DataFrame, boundary column indices as float32).
    """
    diffs = data.diff(axis=1).drop(columns=data.columns[0])
    diffs.loc['changes'] = np.sum(diffs.abs(), axis=0)
    boundaries = np.where(diffs.loc['changes']>min_diff)[0][[0,-1]]
    return diffs, diffs.columns[boundaries].astype(float)

def load_json_file(path):
    """Load json file."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading JSON file from {path}: {e}")
            return None

def get_sampling_bounds_for_cost_param(args, cost_param, cost_boundaries_dict):
    """
    Return lower and upper sampling bounds for one cost parameter.

    For log sampling, bounds are returned in log10-space.
    For linear sampling, bounds are returned in the original multiplier space.
    """
    if args.use_cost_boundaries:
        lower_limit, upper_limit = [float(x) for x in cost_boundaries_dict[cost_param]]
    else:
        lower_limit, upper_limit = float(args.lower_limit), float(args.upper_limit)
    if lower_limit > upper_limit:
        lower_limit, upper_limit = upper_limit, lower_limit
    if args.sampling_method == "log":
        if lower_limit <= 0 or upper_limit <= 0:
            raise ValueError(f"Logarithmic sampling requires positive bounds for {cost_param}. Got lower={lower_limit}, upper={upper_limit}.")
        if not args.interpret_limit_as_exponents:
            lower_limit = np.log10(lower_limit)
            upper_limit = np.log10(upper_limit)
        scale = "log10"
    elif args.sampling_method == "lin":
        if args.interpret_limit_as_exponents:
            lower_limit = 10 ** lower_limit
            upper_limit = 10 ** upper_limit
        scale = "linear"
    elif args.sampling_method in ['sobol', 'lhs']:
        scale='undefined' 
    else:
        raise ValueError(f"Unknown sampling method: {args.sampling_method}")
    return lower_limit, upper_limit, scale

def create_cost_multiplier_design(args, changed_cost_params):
    """
    Create a multi-dimensional Sobol or Latin Hypercube design.

    args.num_of_optimization is interpreted as the total number of sampled
    configurations, not as the number of points per cost parameter.
    """
    n_samples = args.num_of_optimization
    n_dimensions = len(changed_cost_params)

    bounds = {}
    scales = {}

    for ccp in changed_cost_params:
        lower, upper, scale = get_sampling_bounds_for_cost_param(args=args, cost_param=ccp, cost_boundaries_dict=load_json_file(args.cost_boundaries_path))
        bounds[ccp] = (lower, upper)
        scales[ccp] = scale

    if args.sampling_method == "sobol":
        sampler = qmc.Sobol(d=n_dimensions, rng=42)
        # Sobol balance is best for powers of two.
        # We generate the next power of two and then keep the requested number.
        unit_samples = sampler.random_base2(m=int(np.ceil(np.log2(n_samples))))[:n_samples]
    elif args.sampling_method == "lhs":
        sampler = qmc.LatinHypercube(d=n_dimensions, rng=42)
        unit_samples = sampler.random(n=n_samples)
    else:
        raise ValueError(f"Unknown sampling method. Use 'sobol' or 'lhs'. Got: {args.sampling_method}")
    
    designs = []

    for row in unit_samples:
        cost_multipliers = {}
        for j, cp in enumerate(changed_cost_params):
            lower, upper = bounds[cp]
            sampled_value = lower + row[j] * (upper - lower)
            if scales[cp] == "log10":
                multiplier = 10 ** sampled_value
            else:
                multiplier = sampled_value
            cost_multipliers[cp] = float(multiplier)
        designs.append(cost_multipliers)
    return designs

def canonicalize_cost_multipliers(cost_multipliers, log10_decimals=8):
    """
    Convert raw float multipliers to a canonical representation.

    The hash is computed from rounded log10 multipliers, so tiny floating point
    differences do not create different run IDs.
    """
    canonical_log10 = {}
    canonical_multipliers = {}
    for cp, value in cost_multipliers.items():
        canonical_log10[cp] = round(np.log10(value), int(log10_decimals))
        canonical_multipliers[cp] = value
    return canonical_multipliers, canonical_log10


def make_run_id(hash_payload):
    """Create a stable hash from a canonical JSON payload."""
    payload_as_text = json.dumps(hash_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.blake2b(payload_as_text.encode("utf-8"), digest_size=8).hexdigest()

def make_run_metadata(args, raw_cost_multipliers):
    """
    Create metadata and a hash-based run ID for one sampled configuration.
    """

    canonical_multipliers, canonical_log10 = canonicalize_cost_multipliers(raw_cost_multipliers)
    changed_cost_params = sorted(canonical_multipliers.keys())

    run_id = make_run_id({
        "changed_cost_params": changed_cost_params,
        "changed_technologies": args.changed_technologies,
        "canonical_log10_cost_multipliers": canonical_log10
    })

    metadata = {
        "run_id": run_id,
        "canonical_cost_multipliers": canonical_multipliers,
        "canonical_log10_cost_multipliers": canonical_log10,
        "changed_cost_params": changed_cost_params,
        "changed_technologies": args.changed_technologies,
        "sampling_method": getattr(args, "sampling_method"),
    } 
    return run_id, metadata

def apply_multiple_cost_changes(costs_generator, technologies, cost_multipliers):
    """
    Apply multiple cost changes to the same cost dictionary before optimization.

    The optimization is called only once after all requested cost parameters
    have been modified.
    """
    for cp, multiplier in cost_multipliers.items():
        change_costs(
            costs_generator,
            technologies=technologies,
            cost_params=[cp],
            allow_rand_seed=False,
            function="constant",
            x=multiplier,
        )
    return None

def load_nws_and_jsons(folder):
    """
    Load networks and json files from a given folder.
    """
    json_file = next(folder.glob("*.json"), None)
    nc_file = next(folder.glob("*.nc"), None)
    if json_file is None or nc_file is None:
        print(f'Missing data for folder {folder.name}')
        return False
    metadata = load_json_file(json_file)
    network = pypsa.Network(nc_file)
    p_nom_opt = pd.concat((network.generators["p_nom_opt"], network.storage_units["p_nom_opt"]))
    return folder.name, {"metadata": metadata, "nw": network, "p_nom_opt": p_nom_opt}, p_nom_opt.to_numpy()