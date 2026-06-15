# Power Systems Modelling with PyPSA

This repository contains power system modelling work using [PyPSA](https://docs.pypsa.org/), focusing on a dataset based on a future Hungarian electricity system. It includes network optimization, sensitivity analysis and multi-country simulations.

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
| `06_pypsa_eur.ipynb` | PyPSA-Eur integration: short study of PyPSA-Eur and its possibilities |
| `07_sensitivity_test.py` | Script running sensitivity analysis over capital/operational cost multipliers |
| `08_sensitivity_test_result.ipynb` | Visualization of sensitivity test results (line plots, heatmaps) |

## Utilities (`utils.py`)

| Function | Purpose |
|----------|---------|
| `build_and_optimize_network()` | Build and optimize a PyPSA network with generators, storage units, and demand profile |
| `change_costs()` | Apply a function to modify cost parameters for specified technologies |
| `change_generator_p_nom_max()` | Generate randomized maximum generator potentials |
| `change_storage_p_nom_max()` | Generate randomized maximum storage potentials |
| `float_sort_key()` | Extract a float from a filename stem for numeric sorting |
| `read_nc_data()` | Load optimized `.nc` files and compute absolute and normalized capacities |
| `calc_diff()` | Compute differences between consecutive columns and detect change boundaries |
| `plot_generator_t()` | Matplotlib stacked bar chart of dispatch with storage overlay |
| `plot_generator_t_plotly()` | Interactive Plotly version of the dispatch chart |
| `plot_links()` | Faceted seaborn line plots of inter-country link flows |
| `create_lineplot()` | Sensitivity line plot of optimized capacity vs cost multiplier |
| `create_heatmap()` | Sensitivity heatmap of normalized capacity changes |

## Setup

```bash
python3 -m venv .powersys
source .powersys/bin/activate
pip install -r requirements.txt
```

### Dependencies

`pypsa`, `pandas`, `numpy`, `matplotlib`, `plotly`, `seaborn`, `scipy`, `linopy`, `openpyxl`, `nbformat`, `scikit-learn`

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
