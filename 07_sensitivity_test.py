print('--- Start script. ---')
########################################################

from utils import data_path, cost_params, week_numbers
from utils import change_costs
import numpy as np
import pandas as pd
import pypsa
from tqdm import tqdm
from datetime import datetime
import argparse
import os
print('--- Packages imported. ---')

########################################################

folder='data/sensitivity_test/'+datetime.now().strftime("%Y-%m-%d-%H-%M")
os.makedirs(folder)
print('--- Data folder created. ---')

########################################################

parser = argparse.ArgumentParser(description="Run PyPSA optimization in a loop.")
parser.add_argument('-l', "--num_of_loop", type=int, default=100,
                    help="*")
parser.add_argument('-p', "--change_percentage", type=float, default=0.2,
                    help="*")
parser.add_argument('-c', "--changed_cost_params", nargs="+", default=['operation'],
                    help="*")
parser.add_argument('-t', "--changed_technologies", nargs="+", 
                    default=['Solar', 'Wind Onshore', 'Fossil Lignite', 'Nuclear'],
                    help="*")
args = parser.parse_args()

########################################################

dates = []
start_date = pd.to_datetime('2000-01-01') # dummy start date
for week in week_numbers.values():
    s = start_date + pd.Timedelta(weeks=week-1)
    e = s + pd.Timedelta(days=6, hours=23)
    dates.append(pd.date_range(start=s ,end=e, freq='h').to_list())

########################################################

potentials_generator = pd.read_excel(data_path, sheet_name='potentials_generator', index_col=0, na_values='None')
potentials_storage = pd.read_excel(data_path, sheet_name='potentials_storage', index_col=0, na_values='None')
costs_storage = pd.read_excel(data_path, sheet_name='costs_storage', index_col=0, na_values='None').to_dict()
profile_wind = pd.read_excel(data_path, sheet_name='profile_wind', names=list(week_numbers.keys()), header=None, index_col=0)
profile_PV = pd.read_excel(data_path, sheet_name='profile_PV', names=list(week_numbers.keys()), header=None, index_col=0)
demand = pd.read_excel(data_path, sheet_name='demand').values.ravel()
print('--- Data loaded. ---')

########################################################

print('--- Start optimizations. ---')
for i in tqdm(range(args.num_of_loop)):
    costs_generator = pd.read_excel(data_path, sheet_name='costs_generator', index_col=0, na_values='None').to_dict()

    if i!=0:
        change_costs(costs_generator,
                    technologies=args.changed_technologies,
                    cost_params=args.changed_cost_params, 
                    allow_rand_seed=False,
                    function='constant', 
                    x=np.random.uniform(1-args.change_percentage,1+args.change_percentage)
                    )

    # Building the network
    network = pypsa.Network(name='Network')

    # Time stamps
    snapshots = np.array([item for sublist in dates for item in sublist])
    network.set_snapshots(list(snapshots))

    # Base electrical network
    network.add(class_name="Bus", name="country_0", carrier='AC')

    # Set a carrier for the network
    network.add(class_name='Carrier', name='AC')

    # Add demand to the network
    network.add(class_name="Load", name="Residential demand",  bus="country_0", p_set=demand)  

    # Save cost parameters to the network
    network.meta['costs_generator']=costs_generator
    network.meta['costs_storage']=costs_storage 

    # Add generators to the network
    for technology in potentials_generator.keys(): 
        p_max_pu=1
        p_min_pu=0
        #committable=False

        # getting profiles 
        if technology in ['Solar']:
            p_max_pu=np.repeat(profile_PV.values, 7, axis=1).flatten('F') # column-major order
        elif technology in ['Wind Onshore']:
            p_max_pu=np.repeat(profile_wind.values, 7, axis=1).flatten('F')
        elif technology in ['Nuclear']:
            p_min_pu=0.8
            #committable=True
        
        # adding generators
        network.add(class_name="Generator", 
                    name=str(technology),
                    #nicename=str(technology),
                    bus="country_0",
                    
                    p_nom=potentials_generator.loc['p_nom'][str(technology)],
                    p_nom_extendable=True, # optimisable generator capacity
                    p_nom_max=potentials_generator.loc['p_nom_max'][str(technology)], # maximum limit
                    p_nom_min=potentials_generator.loc['p_nom_min'][str(technology)], # minimum limit
                    capital_cost=costs_generator[str(technology)]['capital'], # generator installation cost
                    marginal_cost=sum([costs_generator[str(technology)][key] for key in cost_params]), # operating cost
                    p_max_pu=p_max_pu, # maximum power per-unit // production profiles
                    p_min_pu=p_min_pu,
                    ramp_limit_up=potentials_generator.loc['ramp_up'][str(technology)],   # maximum increase per hour
                    ramp_limit_down=potentials_generator.loc['ramp_down'][str(technology)], # maximum decrease per hour

                    #committable=committable,
                    #ramp_limit_start_up=0.75,
                    #ramp_limit_shut_down=0.75
                )
    
    # Storage units creation
    for technology in potentials_storage.keys():
        network.add(class_name="StorageUnit", 
                    name=str(technology),
                    bus="country_0",
                    
                    p_nom_extendable=True, # optimisable storage capacity
                    p_nom_max=potentials_storage.loc['p_nom_max'][str(technology)], # maximum limit
                    capital_cost=costs_storage[str(technology)]['capital'], # installation cost
                    marginal_cost=sum([costs_storage[str(technology)][key] for key in cost_params]), # operating cost
                )
        
    # Optimization
    network.sanitize()
    result = network.optimize(solver_name='highs', 
                    log_to_console=False,
                    solver_options={'presolve': 'on', 
                                    'threads': 'all',
                                    'solver': 'simplex', # simplex/ipm/pdlp
                                    }
                    )

    network.export_to_netcdf(folder+f"/run_{i}_{result[0]}_{result[1]}.nc")
