# Power Systems Modelling with PyPSA

This repository contains power system modelling work using [PyPSA](https://docs.pypsa.org/), focusing on a dataset based on a future Hungarian electricity system. It includes network optimization, sensitivity analysis and multi-country simulations.

## Notebooks

| Notebook | Description |
|----------|-------------|
| `00_data_exploration.ipynb` | Explore the Hungarian dataset: generator/storage potentials, seasonal demand, solar/wind profiles |
| `01_pypsa_sandbox.ipynb` | Single-week optimization sandbox |
| `02_hungary.ipynb` | 4-season (Spring/Summer/Autumn/Winter) optimization of the Hungarian system |
| `03_random_countries.ipynb` | Multi-country simulation with interconnected buses |
| `04_visualization.ipynb` | Visualization of multi-country optimization results (dispatch, trading, connections) |
| `05_pypsa_params.ipynb` | PyPSA generator & storage unit parameter reference |
| `06_pypsa_eur.ipynb` | PyPSA-Eur integration: installation, datasets, and possibilities |
| `08_sensitivity_test_result.ipynb` | Visualization of single-parameter sensitivity results (line plots, heatmaps) |
| `09_mixed_sensitivity_test_result.ipynb` | Visualization of mixed multi-parameter sensitivity results (Sobol/LHS sampling, cosine/euclidean similarity, clustering, PCA) |

## Scripts

| Script | Purpose |
|--------|---------|
| `07_sensitivity_test.py` | Run sensitivity analysis over cost multipliers. Single-parameter modes (`lin`, `log`) or multi-parameter modes (`sobol`, `lhs`). See `python 07_sensitivity_test.py --help` for all options (save path, baseline, bounds, technologies, limits). |

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
| `load_json_file()` | Load a JSON file, returning `None` on missing/invalid file |
| `get_sampling_bounds_for_cost_param()` | Return lower/upper sampling bounds for one cost parameter (log/lin handling) |
| `create_cost_multiplier_design()` | Create a multi-dimensional Sobol or Latin Hypercube cost-multiplier design |
| `canonicalize_cost_multipliers()` | Canonicalize float multipliers via rounded log10 values |
| `make_run_id()` | Create a stable hash run ID from a canonical JSON payload |
| `make_run_metadata()` | Create metadata and hash-based run ID for one sampled configuration |
| `apply_multiple_cost_changes()` | Apply multiple cost-parameter changes before a single optimization |
| `load_nws_and_jsons()` | Load a network (`.nc`) plus metadata (`.json`) from a result folder |

## Visualizations (`visualizations.py`)

| Function | Purpose |
|----------|---------|
| `plot_generator_t()` | Matplotlib stacked bar chart of dispatch with storage overlay |
| `plot_generator_t_plotly()` | Interactive Plotly version of the dispatch chart |
| `plot_links()` | Faceted seaborn line plots of inter-country link flows |
| `create_lineplot()` | Sensitivity line plot of optimized capacity vs cost multiplier |
| `create_heatmap()` | Sensitivity heatmap of normalized capacity changes |

## Figures (`figures/`)

Pre-generated outputs, grouped by notebook:

- `figures/00_data_exploration/` — demand, PV and wind profiles (`.pdf`)
- `figures/02_hungary/` — seasonal energy dispatch (`.html`, `.pdf`)
- `figures/04_visualization/` — energy trading and connection maps (`.pdf`)
- `figures/08_sensitivity_test/` — single-parameter line plots, zoomed plots and heatmaps per cost type (`.png`)
- `figures/09_mixed_sensitivity_test/` — clustering/PCA results for Sobol and LHS designs (`.html`)

## Setup

```bash
python3 -m venv .powersys
source .powersys/bin/activate
pip install -r requirements.txt
```

### Dependencies (`requirements.txt`)

`matplotlib`, `numpy`, `pandas`, `scipy`, `linopy`, `pypsa`, `nbformat`, `openpyxl`, `scikit-learn`

Note: notebooks/modules also import `plotly` and `seaborn` — install them if needed:

```bash
pip install plotly seaborn
```

## Project Structure

```
.
├── 00_data_exploration.ipynb
├── 01_pypsa_sandbox.ipynb
├── 02_hungary.ipynb
├── 03_random_countries.ipynb
├── 04_visualization.ipynb
├── 05_pypsa_params.ipynb
├── 06_pypsa_eur.ipynb
├── 07_sensitivity_test.py
├── 08_sensitivity_test_result.ipynb
├── 09_mixed_sensitivity_test_result.ipynb
├── utils.py                # Optimization + sensitivity helpers
├── visualizations.py       # Plotting helpers
├── figures/                # Generated figures (tracked)
├── requirements.txt        # Python dependencies
├── LICENSE                 # MIT
└── README.md
```

Note: input datasets, raw `.nc` results, local virtual environments, and other gitignored paths are intentionally not documented here.

## Author

Balázs Menkó — [HUN-REN Centre for Energy Research](https://www.ek.hun-ren.hu/en/home/)
