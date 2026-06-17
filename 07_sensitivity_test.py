print('--- Start script. ---')

###########################################################

from utils import data_path, cost_params, week_numbers, tech_colors
from utils import change_costs, build_and_optimize_network
from utils import create_cost_multiplier_design, make_run_metadata, apply_multiple_cost_changes
import numpy as np
import pandas as pd
import argparse
import copy
import json
from pathlib import Path
import os
from glob import glob
print('--- Packages imported. ---')

###########################################################

parser = argparse.ArgumentParser(description="Run sensitivity analysis by scaling cost parameters across a range of multipliers.")
parser.add_argument('-f', "--function", 
                    type=str, 
                    choices=['lin', 'log'], 
                    required=True,
                    help="Spacing function for cost multipliers: 'lin' for linear, 'log' for logarithmic."
                    )
parser.add_argument('-n', "--num_of_optimization", 
                    type=int, 
                    default=41,
                    help="Number of optimization runs (points in the multiplier range). \nDefault: 41"
                    )
parser.add_argument('-l', "--lower_limit", 
                    type=float, 
                    default=0.001,
                    help="Lower bound of the cost multiplier range. \nDefault: 0.001"
                    )
parser.add_argument('-u', "--upper_limit", 
                    type=float, 
                    default=1000,
                    help="Upper bound of the cost multiplier range. \nDefault: 1000"
                    )
parser.add_argument('-e', "--interpret_limit_as_exponents", 
                    type=bool, 
                    default=False, 
                    action=argparse.BooleanOptionalAction,
                    help="Interpret lower/upper limits as exponent (10^x) values. \nDefault: False"
                    )
parser.add_argument("--filtering_factor", 
                    type=float, 
                    default=0.1,
                    help="Filtering factor for cost multipliers. \nDefault: 0.1"
                    )
parser.add_argument('-c', "--changed_cost_params", 
                    nargs="+", 
                    default=cost_params,
                    help="Cost parameters to vary (capital, environment, operation, reliabiliy and risk). \nDefault: all cost types."
                    )
parser.add_argument('-t', "--changed_technologies", 
                    nargs="+", 
                    default=list(tech_colors.keys())[:13],
                    help="Technologies whose costs are modified. \nDefault: all technolies."
                    )
parser.add_argument('-s', "--save_path", 
                    type=str, 
                    default='data/sensitivity_test/mixed/',
                    help="Directory to save resulting network files. \nDefault: 'data/sensitivity_test/mixed/'"
                    )
parser.add_argument('-b', "--create_baseline", 
                    type=bool, 
                    default=False,
                    action=argparse.BooleanOptionalAction,
                    help="Create a baseline optimization run before the sensitivity scans. \nDefault: False"
                    )
parser.add_argument("--baseline_name", 
                    type=str, 
                    default='baseline_1',
                    help="Name for the baseline network file. \nDefault: 'baseline_1'"
                    )
parser.add_argument('-p', "--parallel_cost_param_change",
                    type=bool, 
                    default=False,
                    action=argparse.BooleanOptionalAction,
                    help="** \nDefault: False"
                    )
parser.add_argument('-m', "--sampling_method",
                    type=str,
                    default="sobol",
                    choices=["sobol", "lhs"],
                    help="Sampling method for the multi-dimensional cost multiplier design.",
                    )
parser.add_argument("--use_cost_boundaries",
                    type=bool, 
                    default=True,
                    action=argparse.BooleanOptionalAction,
                    help="** \nDefault: True"
                    )
parser.add_argument("--cost_boundaries_dict", 
                    type=str, 
                    default='data/sensitivity_test/cost_boundaries.json',
                    help="Directory to save resulting network files. \nDefault: 'data/sensitivity_test/cost_boundaries.json'"
                    )
args = parser.parse_args()
if args.interpret_limit_as_exponents:
    if args.upper_limit > 6:
        print(f"Warning: Too high upper_limit={args.upper_limit}. Do not use '-e'/'--interpret_limit_as_exponents'")
        exit() 
if not args.interpret_limit_as_exponents:
    if args.lower_limit <= 0:
        print(f"Warning: Too low lower_limit={args.lower_limit}. Use positive number.'")
        exit() 

###########################################################

os.makedirs(args.save_path, exist_ok=True)
print('--- Data folder created. ---')

###########################################################

dates = []
start_date = pd.to_datetime('2000-01-01') # dummy start date
for week in week_numbers.values():
    s = start_date + pd.Timedelta(weeks=week-1)
    e = s + pd.Timedelta(days=6, hours=23)
    dates.append(pd.date_range(start=s ,end=e, freq='h').to_list())

###########################################################

potentials_generator = pd.read_excel(data_path, sheet_name='potentials_generator', index_col=0, na_values='None')
potentials_storage = pd.read_excel(data_path, sheet_name='potentials_storage', index_col=0, na_values='None')
costs_storage = pd.read_excel(data_path, sheet_name='costs_storage', index_col=0, na_values='None').to_dict()
costs_generator = pd.read_excel(data_path, sheet_name='costs_generator', index_col=0, na_values='None').to_dict()
profile_wind = pd.read_excel(data_path, sheet_name='profile_wind', names=list(week_numbers.keys()), header=None, index_col=0)
profile_PV = pd.read_excel(data_path, sheet_name='profile_PV', names=list(week_numbers.keys()), header=None, index_col=0)
demand = pd.read_excel(data_path, sheet_name='demand').values.ravel()
print('--- Data loaded. ---')

###########################################################

if args.create_baseline:
    print('--- Create baseline. ---')
    network = build_and_optimize_network(args.baseline_name, costs_generator, costs_storage, dates, demand, 
                                        potentials_generator, potentials_storage, profile_PV, profile_wind, args.save_path)

###########################################################

if not args.parallel_cost_param_change:
    print('--- Start solo optimizations. ---')
    for cp in cost_params:
       os.makedirs(args.save_path+'/'+cp, exist_ok=True)
    f_space = np.linspace if args.function == 'lin' else np.logspace
    if args.function == 'log' and not args.interpret_limit_as_exponents:
        args.lower_limit, args.upper_limit = np.log10(args.lower_limit), np.log10(args.upper_limit)
    if args.function == 'lin' and args.interpret_limit_as_exponents:
        args.lower_limit, args.upper_limit = 10**args.lower_limit, 10**args.upper_limit
    print(f"--- Boundaries: min={args.lower_limit}; max={args.upper_limit}. ---")
    cost_multipliers = f_space(args.lower_limit, args.upper_limit, args.num_of_optimization)

    for cp in args.changed_cost_params:
        runned_simulations = glob(args.save_path+'/'+cp+'/*')
        existing_multipliers = [float(item.split('/')[-1].split('_')[-1].split('.nc')[0]) for item in runned_simulations]
        # exclude multipliers that are within +/-X% of any existing multiplier
        cost_multipliers_filtered = [x for x in cost_multipliers
                                    if not any(abs(x - ex) / max(abs(ex), 1e-12) <= args.filtering_factor for ex in existing_multipliers)]
        print(f'--- {cp}: {len(cost_multipliers_filtered)} out of {len(cost_multipliers)} multipliers will be simulated. ---')
        for x in cost_multipliers_filtered:
            costs_generator = pd.read_excel(data_path, sheet_name='costs_generator', index_col=0, na_values='None').to_dict()
            change_costs(costs_generator, technologies=args.changed_technologies, cost_params=[cp], allow_rand_seed=False, function='constant', x=x)
            build_and_optimize_network(cp+'_'+str(np.round(x,7)), costs_generator, costs_storage, dates, demand, 
                                       potentials_generator, potentials_storage, profile_PV, profile_wind, args.save_path+cp+'/')
else:
    print('--- Start parallel optimizations. ---')
    designs = create_cost_multiplier_design(args=args, changed_cost_params=args.changed_cost_params)
    run_root = Path(args.save_path) / ("multi-cost-"+"_".join(args.changed_cost_params))
    run_root.mkdir(parents=True, exist_ok=True)

    planned_runs, seen_run_ids, = [], set()
    skipped_existing, skipped_duplicate_in_design = 0, 0

    for raw_cost_multipliers in designs:
        run_id, metadata = make_run_metadata(args=args, raw_cost_multipliers=raw_cost_multipliers)
        run_name = f"run_{run_id}"
        run_dir = run_root / run_id
        target_nc_path = run_dir / f"{run_name}.nc"
        metadata_path = run_dir / f"{run_name}.metadata.json"
        if run_id in seen_run_ids:
            skipped_duplicate_in_design += 1
            continue
        seen_run_ids.add(run_id)
        if target_nc_path.exists():
            skipped_existing += 1
            continue
        planned_runs.append({
                "run_id": run_id,
                "run_name": run_name,
                "run_dir": run_dir,
                "target_nc_path": target_nc_path,
                "metadata_path": metadata_path,
                "metadata": metadata,
        })

    print(f"--- {len(planned_runs)} out of {len(designs)} sampled configurations will be simulated. ---")
    if skipped_existing: print(f"--- Skipped existing hash-equivalent runs: {skipped_existing}. ---")
    if skipped_duplicate_in_design: print(f"--- Skipped duplicate sampled configurations: {skipped_duplicate_in_design}. ---")

    for run in planned_runs:
        run["run_dir"].mkdir(parents=True, exist_ok=True)
        with open(run["metadata_path"], "w", encoding="utf-8") as file:
            json.dump(run["metadata"], file, indent=2, sort_keys=True)
        costs_generator_copy = copy.deepcopy(costs_generator)
        apply_multiple_cost_changes(costs_generator=costs_generator_copy, technologies=args.changed_technologies, 
                                    cost_multipliers=run["metadata"]["canonical_cost_multipliers"])
        build_and_optimize_network(run["run_name"], costs_generator_copy, costs_storage, dates, demand, potentials_generator,
                                   potentials_storage, profile_PV, profile_wind, str(run["run_dir"]) + os.sep, save_meta_data=run["metadata"])

print(f'--- Optimizations are done. ---')
