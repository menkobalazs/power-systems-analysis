################
### Packages ###
################

import re
import os
import pypsa
import itertools
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import plotly.graph_objects as go
from glob import glob
from pathlib import Path
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
    'Storage Actual':'#FF0000'
}

######################################
### Network Optimizations Function ###
######################################

def build_and_optimize_network(name, generator_costs, storage_costs, dates, demand, potentials_generator, potentials_storage, profile_PV, profile_wind, save_path):
    network = pypsa.Network(name=name)
    snapshots = np.array([item for sublist in dates for item in sublist])
    network.set_snapshots(list(snapshots))
    
    network.add("Bus", "country_0", carrier='AC')
    network.add('Carrier', 'AC')
    network.add("Load", "Residential demand", bus="country_0", p_set=demand)  
    
    network.meta['costs_generator'] = generator_costs
    network.meta['costs_storage'] = storage_costs 

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
    network.optimize(
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

def float_sort_key(path):
    stem = Path(path).stem
    match = re.search(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', stem)
    if match:
        return float(match.group(0))
    raise ValueError(f"No numeric parameter found in filename: {path}")

def read_nc_data(path, baseline):
    nws = {}
    nws_normed = {}
    for file in sorted(glob(path), key=float_sort_key):
        nw = pypsa.Network(file)
        nw_name = nw.name.split('_')
        max_capacities = pd.concat((nw.generators.p_nom_opt.abs(), nw.storage_units.p_nom_opt.abs()))
        nws[nw_name[1]] = np.round(max_capacities, 3)
        nws_normed[nw_name[1]] = max_capacities - pd.concat((baseline.generators.p_nom_opt.abs(), baseline.storage_units.p_nom_opt.abs()))
    return pd.DataFrame(nws), pd.DataFrame(nws_normed)


###############################
### Visualization Functions ###
###############################

def plot_generator_t(network, dates, season, day, colors=tech_colors, country=None, demand=[], savefig=''):
    """
    Plot the optimal energy generation dispatch for a specific season and day, including storage unit activity.
    """
    if type(season) == str: 
        season = seasons[season]
    if season < 1 or season > 4:
        raise ValueError("Season must be between 1 and 4.")
    if day < 1 or day > 8:
        raise ValueError("Day must be between 1 and 7.")
    start = dates[season-1][(day-1)*24] 
    end = dates[season-1][(day-1)*24+23]
    #---------
    if type(country) == str: country = int(country.split('_')[1])
    elif type(country) == int or country == None: pass
    else: raise ValueError("country should be either a string like 'country_1'"+\
                           " or an integer representing the country number or None.")    

    if country != None:
        if 'nicename' in network.generators.keys():
            technologies=network.generators.nicename.values[country*13:(country+1)*13]
        else:
            technologies=network.generators.index
        generators_t_p = network.generators_t.p.iloc[:, country*13:(country+1)*13]
        generators_t_p.columns = technologies
        storage_units_t_p = network.storage_units_t.p.iloc[:, country*2:(country+1)*2]
        storage_units_t_p.columns = list(tech_colors.keys())[-2:]
    else:
        generators_t_p = network.generators_t.p
        storage_units_t_p = network.storage_units_t.p
    generators_t_p = generators_t_p.loc[start:end, generators_t_p.abs().sum() > 0]
    generators_t_p.index = generators_t_p.index.hour
    generators_t_p = generators_t_p[generators_t_p.max().sort_values(ascending=False).index]# Sort columns by mean generation descending
    ax = generators_t_p.plot(kind='bar', figsize=(10,5), stacked=True, color=colors)
    if storage_units_t_p.shape[1]:
        storage_units_t_p = storage_units_t_p.loc[:, storage_units_t_p.abs().sum() > 0]  # only active storages
        storage_units_t_p = storage_units_t_p.loc[start:end]
        storage_units_t_p.index = storage_units_t_p.index.hour
        storage_units_t_p.plot(ax=ax, style='-o', linewidth=1.5, markersize=4, legend=True, color=colors)
    if len(demand): 
        ax.plot(demand[24*(7*(season-1)+day-1):24*(7*(season-1)+day)], 
                'o--', color='black', linewidth=1.5, markersize=4, label='Demand')
    else:
        ax.set_ylim(np.round(storage_units_t_p.sum(axis=1).min(), -2)-100, 
                       np.round(generators_t_p.sum(axis=1).max(), -2)+100)
    ax.legend(bbox_to_anchor=(1, 1), loc='upper left', fontsize=7)
    ax.set_xlabel('Time [h]')
    ax.set_ylabel('Power [MWh]')
    ax.set_title(f"Optimal Energy Generation Dispatch\n{list(seasons.keys())[season-1]} -- Day {day}"+\
                 (f" -- Country {country}" if country is not None else "")
                )
    ax.set_xticks(range(0, len(generators_t_p.index)))
    ax.set_xticklabels(generators_t_p.index, rotation=0)
    plt.tight_layout()
    plt.grid(axis='y', linestyle='--', alpha=0.8)
    if savefig: plt.savefig(savefig, bbox_inches='tight')
    plt.show()
    return None

def plot_generator_t_plotly(network, dates, season, colors, savefig=''):
    """
    Plot the optimal energy generation dispatch for a specific time range using Plotly, including storage unit activity.
    """
    os.makedirs("figures", exist_ok=True)
    title = f'Optimal Energy Generation - {season}'
    if type(season) == str: 
        season = seasons[season]
    if season < 1 or season > 4:
        raise ValueError("Season must be between 1 and 4.")
    start = dates[season-1][0] 
    end = dates[season-1][-1]
    df = network.generators_t.p.loc[start:end]
    df = df.loc[:, df.mean() > 0].copy()
    df = df[df.sum().sort_values(ascending=False).index]
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Bar(x=df.index, y=df[col], name=col, marker_color=colors.get(col), offsetgroup=0))
    storage_p = network.storage_units_t.p.loc[start:end]
    active_storage = storage_p.columns[(storage_p != 0).any()]
    if not active_storage.empty:
        for tech in active_storage:
            fig.add_trace(go.Scatter(x=storage_p.index, y=storage_p[tech], mode='lines', 
                                     name=tech, line=dict(color=colors.get(tech), width=2.5), connectgaps=False))
    fig.update_layout(
        title=title, barmode='stack', template='plotly_white', hovermode='x unified',
        xaxis=dict(title='Time', rangeslider=dict(visible=True), type='date'),
        yaxis=dict(title='Power [MWh]'),
        legend=dict(font=dict(size=10), orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(l=50, r=150, t=80, b=50)
    )
    if savefig: fig.write_html(savefig, include_plotlyjs='cdn')
    return None

def plot_links(network, dates, season, day, savefig=''):
    if type(season) == str: 
        season = seasons[season]
    if season < 1 or season > 4:
        raise ValueError("Season must be between 1 and 4.")
    if day < 1 or day > 8:
        raise ValueError("Day must be between 1 and 7.")
    start = dates[season-1][(day-1)*24] 
    end = dates[season-1][(day-1)*24+23]
    df = network.links_t.p0.melt(ignore_index=False, var_name="Link", value_name="Flow").reset_index()
    df.rename(columns={df.columns[0]: "Snapshot"}, inplace=True)
    df = df[(df.Snapshot >= start) & (df.Snapshot <= end)]
    g = sns.FacetGrid(df, col="Link", col_wrap=4, height=3, sharey=True)
    g.map(sns.lineplot, "Snapshot", "Flow")
    for ax in g.axes.flat:
        ax.tick_params(axis='x', rotation=45)
    for ax, title in zip(g.axes.flat, df['Link'].unique()):
        country_id = str(title).split("_")
        clean_title = f"Link: {country_id[1]} → {country_id[2]}"
        ax.set_title(clean_title,  fontsize=10, pad=10)
    plt.tight_layout()
    if savefig: plt.savefig(savefig, bbox_inches='tight')
    plt.show()
    return None

def create_lineplot(data, title, xlim=(None, None), savefig=''):
    df_env = data.T
    df_env.index = df_env.index.astype(float)
    df_env.sort_index(inplace=True)
    marker_styles = ["+", 'o', 'x']
    marker_pool = itertools.cycle(marker_styles)
    plt.figure(figsize=(12,6))
    for tech in df_env.columns:
        plt.plot(df_env.index, df_env[tech],
                label= tech if max(df_env[tech]) else f"{tech} (always zero)",
                color=tech_colors.get(tech, '#333333'),
                linewidth=1,
                marker=next(marker_pool),
                markersize=4,  
                linestyle='dotted',
                alpha= 0.9 if max(df_env[tech]) else 0.4)
    plt.xscale('log')
    plt.xlim(xlim)
    idx = df_env.index.astype(float)
    idx_pos = idx[idx > 0]
    if not idx_pos.empty:
        xticks = np.logspace(np.log10(idx_pos.min()), np.log10(idx_pos.max()), num=20)
        xtick_labels = [f"{x:.2e}" for x in xticks]
        plt.xticks(xticks, xtick_labels, rotation=45, ha='center')
    plt.axhline(0, color='gray', linewidth=0.8, alpha=0.7)
    plt.grid(which='both', linestyle='dotted')
    plt.legend(title='Technologies', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=10)
    plt.title(f"Impact of {title} Cost", fontsize=16)
    plt.xlabel('Cost Multiplier', fontsize=12)
    plt.ylabel(r'Optimised capacity [MWh]', fontsize=12)
    plt.tight_layout()
    if savefig: plt.savefig(savefig, bbox_inches='tight')
    plt.show()
    return None
    
def create_heatmap(data, title='', savefig=''):
    plt.figure(figsize=(12,6))
    norm = colors.SymLogNorm(linthresh=1.0, vmin=data.min().min(), vmax=data.max().max(), base=10)
    ax = sns.heatmap(data, cmap='coolwarm', norm=norm, cbar_kws={'label': r'Normalized optimised capacity [MWh]'} )
    plt.title(f"Impact of {title} Cost", fontsize=16)
    plt.xlabel('Cost Multiplier', fontsize=12)
    plt.ylabel("Power Plant Types", fontsize=12)
    tick_positions = np.linspace(0, data.shape[1]-1, 20, dtype=int)
    ax.set_xticks(tick_positions + 0.5)
    ax.set_xticklabels([f"{float(data.columns[i]):.2e}" for i in tick_positions], rotation=45, ha='center')
    plt.tight_layout()
    if savefig: plt.savefig(savefig, bbox_inches='tight')
    plt.show()
    return None