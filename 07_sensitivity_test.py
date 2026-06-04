print('--- Start script. ---')

###########################################################

from utils import data_path, cost_params, week_numbers, tech_colors
from utils import change_costs, build_and_optimize_network
import numpy as np
import pandas as pd
import argparse
import os
from glob import glob
print('--- Packages imported. ---')

###########################################################

parser = argparse.ArgumentParser(description="Run sensitivity analysis by scaling cost parameters across a range of multipliers.")
parser.add_argument('-f', "--function", type=str, choices=['lin', 'log'], required=True,
                    help="Spacing function for cost multipliers: 'lin' for linear, 'log' for logarithmic.")
parser.add_argument('-l', "--lower_limit", type=float, default=0.001,
                    help="Lower bound of the cost multiplier range.")
parser.add_argument('-u', "--upper_limit", type=float, default=1000,
                    help="Upper bound of the cost multiplier range.")
parser.add_argument('-g', '--set_limit_log_scale', type=bool, default=False, action=argparse.BooleanOptionalAction,
                    help="Interpret lower/upper limits as decimal values when using log spacing.")
parser.add_argument('-e', '--set_limit_exp_scale', type=bool, default=False, action=argparse.BooleanOptionalAction,
                    help="Interpret lower/upper limits as exponents (10^x) when using linear spacing.")
parser.add_argument('-n', "--num_of_optimization", type=int, default=41,
                    help="Number of optimization runs (points in the multiplier range).")
parser.add_argument("--filtering_factor", type=float, default=0.1,
                    help="Filtering factor for cost multipliers.")
parser.add_argument('-c', "--changed_cost_params", nargs="+", default=cost_params,
                    help="Cost parameters to vary (e.g. investment, fixedom, fuel).")
parser.add_argument('-t', "--changed_technologies", nargs="+", default=list(tech_colors.keys())[:-2],
                    help="Technologies whose costs are modified.")
parser.add_argument('-s', "--save_path", type=str, default='data/sensitivity_test/networks/',
                    help="Directory to save resulting network files.")
parser.add_argument('-b', "--create_baseline", type=bool, default=False, action=argparse.BooleanOptionalAction,
                    help="Create a baseline optimization run before the sensitivity scans.")
parser.add_argument("--baseline_name", type=str, default='baseline_1',
                    help="Name for the baseline network file.")
args = parser.parse_args()

###########################################################

os.makedirs(args.save_path, exist_ok=True)
for cp in cost_params:
    os.makedirs(args.save_path+cp, exist_ok=True)
print('--- Data folders created. ---')

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

print('--- Start optimizations. ---')
f_space = np.linspace if args.function == 'lin' else np.logspace
if args.function == 'log' and args.set_limit_log_scale:
    args.lower_limit, args.upper_limit = np.log10(args.lower_limit), np.log10(args.upper_limit)
if args.function == 'lin' and args.set_limit_exp_scale:
    args.lower_limit, args.upper_limit = 10**args.lower_limit, 10**args.upper_limit
cost_multipliers = f_space(args.lower_limit, args.upper_limit, args.num_of_optimization)

for cp in args.changed_cost_params:
    runned_simulations = glob(args.save_path+cp+'/*')
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


print(f'--- Optimizations are done. ---')

###########################################################

#print('--- Start data processing. ---')
