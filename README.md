# PostFOAM

Automated post-processing and PDF reporting for OpenFOAM simulations.

Drop a YAML config into your case directory, run one command, and get a complete PDF report with residual plots, y+ distributions, time-series data, ParaView renders, and a structured summary of your simulation setup.

![Example Report](examples/sample_report.pdf)

---

## Features

- **Config-driven** — define what to plot in a single YAML file, no Python editing required
- **Residual convergence plots** — automatic parsing of OpenFOAM `residuals.dat`
- **Wall y+ analysis** — per-patch bar charts (min / max / average)
- **Time-series plotting** — probe data, surface field values (pressure, mass flow, etc.)
- **ParaView renders** — optional pvbatch integration for pressure/streamline visualisations
- **Expert Mode** — structured summary of solver settings, numerical schemes, turbulence model, relaxation factors, and decomposition — parsed directly from your OpenFOAM dictionaries
- **Professional PDF output** — dark-themed cover page, section dividers, and clean table layouts via ReportLab

---

## Quick Start

### 1. Install dependencies

```bash
pip install matplotlib reportlab pyyaml
```

### 2. Copy config into your case directory

```bash
cp config.example.yaml /path/to/your/case/config.yaml
```

### 3. Edit the config

Open `config.yaml` and adjust the report metadata and plot entries to match your case. See [Configuration](#configuration) below.

### 4. Run

```bash
cd /path/to/your/case
python /path/to/POSTFOAM/Runner.py --config config.yaml
```

Output is saved to `postProcessing/Reports/PostProcessing_Report.pdf`.

### 5. (Optional) ParaView renders

If you want to include ParaView visualisations, run the ParaView step **before** the main runner:

```bash
pvbatch /path/to/POSTFOAM/Runner_pv.py
python /path/to/POSTFOAM/Runner.py --config config.yaml
```

The runner will automatically pick up the rendered image if it exists at the path specified in the config.

---

## Configuration

The YAML config has two sections: `report` (metadata) and `plots` (what to generate).

```yaml
report:
  title: "CFD Post-Processing Report"
  case_name: "My Simulation"
  author: "Your Name"
  description: "Brief description shown on cover page"
  expert_mode: true          # include parsed dictionary summary of numerical schemes, turbulence modeling, etc.

plots:
  - type: residuals
    file: postProcessing/residuals/0/residuals.dat
    section: "Residuals"
    light_mode: true         # optional, default false

  - type: yplus
    file: postProcessing/yPlus/0/yPlus.dat
    section: "Wall Y+"

  - type: sidepod_pressure
    file: postProcessing/probes/0/p
    section: "Probe Pressure"

  - type: sidepod_massflow
    file: postProcessing/sidepodMassFlowR/0/surfaceFieldValue.dat
    section: "Mass Flow Rate"

  - type: image
    file: postProcessing/images/foam_render.png
    caption: "Pressure & Streamlines"
    section: "Flow Visualisation"
```

### Available plot types

| Type | Description | Required fields |
|------|-------------|----------------|
| `residuals` | Convergence plot from solver residuals | `file`, `section` |
| `yplus` | Per-patch y+ bar charts | `file`, `section` |
| `sidepod_pressure` | Pressure probe time-series (here for sidepods of a car) | `file`, `section` |
| `sidepod_massflow` | Mass flow rate time-series (here for sidepods of a car) | `file`, `section` |
| `image` | Static image (e.g. ParaView render) | `file`, `section`, `caption` |

### Expert Mode

When `expert_mode: true`, the report appends structured summary pages parsed from your OpenFOAM dictionaries:

- `system/controlDict` — solver application, time stepping, write settings, function objects
- `system/fvSchemes` — ddt, grad, div, laplacian, interpolation, snGrad schemes
- `system/fvSolution` — solver types and tolerances, SIMPLE/PIMPLE/PISO settings, relaxation factors
- `system/decomposeParDict` — decomposition method and subdomain count
- `constant/momentumTransport` — turbulence model (RAS/LES) and model name
- `constant/physicalProperties` — kinematic viscosity and transport model

---

## File Structure

```
POSTFOAM/
├── Runner.py                  # Main config-driven entry point
├── Runner_pv.py               # ParaView rendering (runs under pvbatch)
├── config.example.yaml        # Template config — copy to your case
├── base.py                    # Base plotter class
├── Residuals_plotter.py       # Residual convergence plotter
├── Yplus_plotter.py           # Wall y+ plotter
├── sidepodPressurePlotter.py  # Pressure probe time-series plotter
├── sidePodMassflowPlotter.py  # Mass flow time-series plotter
├── PostProcesser.py           # ParaView state/render utilities
├── ReportBuilder.py           # PDF report assembly (ReportLab)
├── DictParser.py              # OpenFOAM dictionary parser
├── README.md
└── LICENSE
```

---

## Requirements

- Python 3.9+
- `matplotlib`
- `reportlab`
- `pyyaml`
- ParaView with `pvbatch` (optional, for flow visualisation renders)

---

## Example Output

An example report generated from an F1 aerodynamics simulation is included in `examples/sample_report.pdf`.

The report contains:
- Residual convergence history
- Per-patch y+ statistics
- Sidepod pressure and mass flow rate time-series
- Expert Mode summary of all simulation parameters

---

## Roadmap

Planned features for future releases:

- **ParaView version config** — specify ParaView version (5.9 / 5.11) in the YAML config, with `Runner_pv.py` and `PostProcesser.py` automatically adapting API calls to match
- **Generic time-series plotter** — unified plotter type replacing case-specific plotters, with axis labels and titles driven from config
- **Mesh quality summary page** — parse `checkMesh` output into the Expert Mode section
- **CLI install** — `pip install postfoam` with a `postfoam run` command

---

## License

See [LICENSE](LICENSE).

---

## Author

Developed by M. Toffoli as part of an F1 aerodynamics CFD thesis project.