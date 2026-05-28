# Power Systems Modelling with PyPSA

This repository contains power system modelling work using [PyPSA](https://docs.pypsa.org/), focusing on a dataset based on a future Hungarian electricity system. It includes network optimization, sensitivity analysis, multi-country simulations, and integration with [PyPSA-Eur](https://pypsa-eur.readthedocs.io/).

## Data

- `data/Adatok_HU_2050.xlsx` — Hungarian electricity system dataset (generator potentials, storage potentials, demand, solar/wind profiles)
- `data/entsoe/` — ENTSO-E data (e.g. `TYNDP_2022.xlsx`)
- `data/results/` — serialized network `.nc` files from optimizations
- `data/sensitivity_test/` — sensitivity test `.nc` outputs

## Notebooks

| Notebook | Description |
|----------|-------------|
| `00_data_exploration.ipynb` | Explore the Hungarian dataset: generator/storage potentials, seasonal demand |
| `01_pypsa_sandbox.ipynb` | Single-week optimization sandbox |
| `02_hungary.ipynb` | 4-season (Spring/Summer/Autumn/Winter) optimization of the Hungarian system |
| `03_random_countries.ipynb` | Multi-country simulation with interconnected buses |
| `04_visualization.ipynb` | Visualization of multi-country optimization results |
| `05_pypsa_params.ipynb` | PyPSA generator & storage unit parameter reference |
| `06_pypsa_eur.ipynb` | PyPSA-Eur integration: cluster extraction, data comparison |
| `07_sensitivity_test.py` | Script running sensitivity analysis over capital/operational cost multipliers |
| `08_sensitivity_test_result.ipynb` | Visualization of sensitivity test results (line plots, heatmaps) |

## Utilities (`utils.py`)

| Function | Purpose |
|----------|---------|
| `build_and_optimize_network()` | Create a PyPSA network with generators + storage units and run optimization |
| `change_costs()` | Apply arbitrary cost multipliers to generator/storage cost parameters |
| `change_generator_p_nom_max()` | Generate randomized maximum potential capacities |
| `change_storage_p_nom_max()` | Generate randomized maximum storage potentials |
| `read_nc_data()` | Load and compare optimized `.nc` results against a baseline |
| `plot_generator_t()` | Matplotlib stacked bar + storage line plot for dispatch |
| `plot_generator_t_plotly()` | Interactive Plotly version of the dispatch chart |
| `plot_links()` | Faceted line plots of inter-country link flows |
| `create_lineplot()` | Sensitivity analysis line plot (capacity vs cost multiplier) |
| `create_heatmap()` | Sensitivity analysis heatmap (normalized capacity change) |

## Setup

```bash
python3 -m venv .powersys
source .powersys/bin/activate
pip install -r requirements.txt
```

### Dependencies

`pypsa`, `pandas`, `numpy`, `matplotlib`, `plotly`, `seaborn`, `scipy`, `linopy`, `openpyxl`, `nbformat`

## Project Structure

```
.
├── data/               # Input data and optimization results
│   ├── entsoe/         # ENTSO-E data
│   ├── results/        # .nc network files
│   └── sensitivity_test/
├── figures/            # Generated figures
├── pypsa-eur/          # PyPSA-Eur submodule
├── .powersys/          # Python virtual environment
├── 00_*.ipynb … 08_*.ipynb  # Jupyter notebooks
├── 07_sensitivity_test.py   # Sensitivity test script
├── utils.py            # Core utility functions
└── requirements.txt    # Python dependencies
```

## Author

Balázs Menkó — [HUN-REN Centre for Energy Research](https://www.ek.hun-ren.hu/en/home/)
