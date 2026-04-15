"""
run.py - Config-driven OpenFOAM post-processing runner.
 
Usage:  python run.py --config config.yaml
        python run.py                       (defaults to config.yaml in cwd)
"""
from __future__ import annotations
 
import argparse
import sys
from pathlib import Path
 
import yaml
 
from Residuals_plotter import ResidualsPlotter
from Yplus_plotter import YPlusPlotter
from sidepodPressurePlotter import SidePodPressurePlotter
from sidePodMassflowPlotter import SidePodMassflowPlotter
from ReportBuilder import ReportBuilder
 
 
# ── Map config "type" strings to plotter classes and their config key ──
PLOTTER_REGISTRY = {
    "residuals":    {"cls": ResidualsPlotter,       "key": "residuals"},
    "yplus":        {"cls": YPlusPlotter,           "key": "yPlus"},
    "sidepod_pressure": {"cls": SidePodPressurePlotter, "key": "sidePodPressure"},
    "sidepod_massflow": {"cls": SidePodMassflowPlotter, "key": "sidePodMassflow"},
}
 
 
def load_config(config_path: Path) -> dict:
    """Load and validate the YAML config file."""
    if not config_path.is_file():
        print(f"[run.py] ERROR: config file not found: {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    if not cfg or "plots" not in cfg:
        print("[run.py] ERROR: config must contain a 'plots' section")
        sys.exit(1)
    return cfg
 
 
def run_plotters(plots_cfg: list[dict], case_dir: Path, out_dir: Path) -> list[tuple[list[Path], str]]:
    """
    Instantiate and run each plotter defined in the config.
 
    Returns a list of (image_paths, section_name) tuples.
    """
    results = []
 
    for entry in plots_cfg:
        plot_type = entry.get("type", "")
 
        # Static images (e.g. ParaView renders) — no plotter needed
        if plot_type == "image":
            img_path = case_dir / entry["file"]
            if img_path.is_file():
                results.append(([img_path], entry.get("section", "")))
            else:
                print(f"[run.py] WARNING: image not found, skipping: {img_path}")
            continue
 
        # Plotter-based entries
        if plot_type not in PLOTTER_REGISTRY:
            print(f"[run.py] WARNING: unknown plot type '{plot_type}', skipping")
            continue
 
        reg = PLOTTER_REGISTRY[plot_type]
        config_key = reg["key"]
 
        # Build the plotter config dict from the YAML entry
        plotter_config = {config_key: {"file": entry["file"]}}
 
        # Pass through any extra options (e.g. light_mode)
        for opt in ("light_mode",):
            if opt in entry:
                plotter_config[config_key][opt] = entry[opt]
 
        plotter = reg["cls"](
            case_dir=case_dir,
            out_dir=out_dir,
            config=plotter_config,
        )
 
        images = plotter.run()
        print(f"[run.py] Generated ({plot_type}): {images}")
        results.append((images, entry.get("section", "")))
 
    return results
 
 
def build_report(report_cfg: dict, case_dir: Path, out_dir: Path,
                 plotter_results: list[tuple[list[Path], str]],
                 image_entries: list[dict]):
    """Assemble and build the PDF report."""
    reports_dir = out_dir / "Reports"
 
    report = ReportBuilder(
        title=report_cfg.get("title", "CFD Post-Processing Report"),
        case_name=report_cfg.get("case_name", ""),
        out_path=reports_dir / "PostProcessing_Report.pdf",
        author=report_cfg.get("author", ""),
        description=report_cfg.get("description", ""),
        case_dir=case_dir,
        include_expert_mode=report_cfg.get("expert_mode", True),
    )
 
    # Add plotter-generated images
    for images, section in plotter_results:
        if section and len(images) == 1 and images[0].suffix in (".png", ".jpg", ".jpeg"):
            # Single static image (e.g. ParaView render) — find its caption from config
            caption = ""
            for ie in image_entries:
                if Path(ie["file"]).name == images[0].name:
                    caption = ie.get("caption", "")
                    break
            report.add_image(images[0], caption=caption, section=section)
        else:
            report.add_images(images, section=section)
 
    report.build()
 
 
def main():
    parser = argparse.ArgumentParser(description="OpenFOAM Post-Processing Runner")
    parser.add_argument("--config", type=str, default="config.yaml",
                        help="Path to YAML config file (default: config.yaml)")
    parser.add_argument("--case-dir", type=str, default="./",
                        help="Path to OpenFOAM case directory (default: ./)")
    args = parser.parse_args()
 
    config_path = Path(args.config)
    case_dir = Path(args.case_dir)
    out_dir = case_dir / "postProcessing"
    img_dir = out_dir / "images"
 
    cfg = load_config(config_path)
    report_cfg = cfg.get("report", {})
    plots_cfg = cfg.get("plots", [])
 
    # Separate image entries (for caption lookup later)
    image_entries = [e for e in plots_cfg if e.get("type") == "image"]
 
    # Run all plotters and collect results
    results = run_plotters(plots_cfg, case_dir, img_dir)
 
    # Build the PDF report
    build_report(report_cfg, case_dir, out_dir, results, image_entries)
 
 
if __name__ == "__main__":
    main()