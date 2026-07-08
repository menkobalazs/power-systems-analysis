################
### Packages ###
################

import os
import itertools
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import plotly.graph_objects as go

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
    'Storage Actual ':'#FF0000', # Due to a typo a version exists with a scape at the end
    'Storage Actual':'#FF0000'
}

###############################
### Visualization Functions ###
###############################

def plot_generator_t(network, dates, season, day, colors=tech_colors, country=None, demand=[], savefig=''):
    """
    Plot the optimal energy generation dispatch for a specific season and day, including storage unit activity.

    Parameters:
    - network: pypsa.Network, optimized network containing generators and storage units.
    - dates: list of lists, snapshot timestamps for each season.
    - season: str or int, season name (e.g. 'Spring') or index (1-4).
    - day: int, day number within the season (1-7).
    - colors: dict, mapping technology names to matplotlib colors. Defaults to tech_colors.
    - country: str, int, or None. If provided, filters to a specific country (e.g. 'country_1' or 1).
    - demand: list, optional demand time series to overlay on the plot.
    - savefig: str, optional file path to save the figure.

    Returns:
    - None
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
    ax.set_ylabel('Power [MW]')
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

def plot_generator_t_plotly(network, dates, season, colors, savefig='', demand=[]):
    """
    Plot the optimal energy generation dispatch for a specific season using Plotly, including storage unit activity.

    Parameters:
    - network: pypsa.Network, optimized network containing generators and storage units.
    - dates: list of lists, snapshot timestamps for each season.
    - season: str or int, season name (e.g. 'Spring') or index (1-4).
    - colors: dict, mapping technology names to plotly color strings.
    - savefig: str, optional file path to save the figure as HTML.

    Returns:
    - None
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
    if len(demand):
        demand = np.asarray(demand)[(season-1)*7*24:season*7*24]
        fig.add_trace(go.Scatter(
            x=df.index,
            y=demand,
            mode='lines+markers',
            name='Demand',
            line=dict(color='black', dash='dash', width=2),
            marker=dict(symbol='circle', size=6, color='black')
        ))
    storage_p = network.storage_units_t.p.loc[start:end]
    active_storage = storage_p.columns[(storage_p != 0).any()]
    if not active_storage.empty:
        for tech in active_storage:
            fig.add_trace(go.Scatter(x=storage_p.index, y=storage_p[tech], mode='lines', 
                                     name=tech, line=dict(color=colors.get(tech), width=2.5), connectgaps=False))
    fig.update_layout(
        title=title, barmode='stack', template='plotly_white', hovermode='x unified',
        xaxis=dict(title='Time', rangeslider=dict(visible=True), type='date'),
        yaxis=dict(title='Power [MW]'),
        legend=dict(font=dict(size=10), orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(l=50, r=150, t=80, b=50)
    )
    if savefig: fig.write_html(savefig, include_plotlyjs='cdn')
    return None

def plot_links(network, dates, season, day, savefig=''):
    """
    Plot power flow on inter-country links for a given season and day using seaborn FacetGrid.

    Parameters:
    - network: pypsa.Network, optimized network containing links.
    - dates: list of lists, snapshot timestamps for each season.
    - season: str or int, season name (e.g. 'Spring') or index (1-4).
    - day: int, day number within the season (1-7).
    - savefig: str, optional file path to save the figure.
    """
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

def create_lineplot(data, title, xlim=None, savefig=''):
    """
    Plot optimized capacity as a function of a cost multiplier across technologies.

    Parameters:
    - data: pd.DataFrame, capacity values indexed by cost multiplier with technologies as columns.
    - title: str, base title describing the cost parameter being varied.
    - xlim: tuple of float, optional x-axis limits for zooming.
    - savefig: str, optional file path to save the figure.
    """
    df_env = data.T
    df_env.index = df_env.index.astype(float)
    df_env.sort_index(inplace=True)
    marker_styles = ["+", 'o', 'x']
    marker_pool = itertools.cycle(marker_styles)
    plt.figure(figsize=(12,6))
    for tech in df_env.columns:
        plt.plot(df_env.index, df_env[tech],
                label= tech if max(df_env[tech]) else f"{tech} (always zero)",
                color=tech_colors.get(tech, '#00FF00'),
                linewidth=1,
                marker=next(marker_pool),
                markersize=4,  
                linestyle='-.',
                alpha= 1 if max(df_env[tech]) else 0.4)
    plt.xscale('log')
    idx = df_env.index.astype(float)
    idx_pos = idx[idx > 0]
    if not idx_pos.empty:
        if xlim is not None: 
            plt.xlim(xlim)
            xticks = np.logspace(np.log10(xlim[0]), np.log10(xlim[1]), num=20)
            print(f'Boundaries: [{xlim[0]:.6f};{xlim[1]:.6f}]')
        else:
            xticks = np.logspace(np.log10(idx_pos.min()), np.log10(idx_pos.max()), num=20)
        xtick_labels = [f"{x:.2e}" for x in xticks]
        plt.xticks(xticks, xtick_labels, rotation=45, ha='center')
    plt.axhline(0, color='gray', linewidth=0.8, alpha=0.7)
    plt.grid(which='both', linestyle='dotted')
    plt.legend(title='Technologies', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=10)
    plt.title(f"Impact of {title} Cost", fontsize=16)
    plt.xlabel('Cost Multiplier', fontsize=12)
    plt.ylabel('Built-in Power [MW]', fontsize=12)
    plt.tight_layout()
    if savefig: plt.savefig(savefig, bbox_inches='tight')
    plt.show()
    return None
    
def create_heatmap(data, title='', savefig=''):
    """
    Plot a heatmap of optimized capacity changes across cost multipliers and technologies.

    Parameters:
    - data: pd.DataFrame, capacity values indexed by cost multiplier with technologies as columns.
    - title: str, base title describing the cost parameter being varied.
    - savefig: str, optional file path to save the figure.
    """
    plt.figure(figsize=(12,6))
    norm = colors.SymLogNorm(linthresh=1.0, vmin=data.min().min(), vmax=data.max().max(), base=10)
    ax = sns.heatmap(data, cmap='coolwarm', norm=norm, cbar_kws={'label': r'$\Delta$P [MW]'} )
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