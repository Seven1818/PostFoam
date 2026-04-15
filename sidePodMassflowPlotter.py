from __future__ import annotations #fix issues with forward references in type hints (DelftBlue PVbatch is old)
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from base import PostStage

class SidePodMassflowPlotter(PostStage): #Class object that inherits from the PostStage base class, responsible for generating mass flow plots inside sidepods from OpenFOAM simulation data
    name = "sidePodMassflow"
    rho = 1.225 # Density of air at sea level in kg/m^3, used to convert volumetric flow rate into mass flow rate
    def run(self) -> list[Path]:
        cfg = self.config.get("sidePodMassflow", {}) # retrieves the configuration settings for the side pod mass flow plotter from the overall configuration dictionary, using "sidePodMassflow" as the key, and defaults to an empty dictionary if no specific settings are found
        file_path = self.case_dir / cfg.get("file", "postProcessing/sidepodMassFlowR/0/surfaceFieldValue.dat") # constructs the file path to the side pod data file by combining the case directory with the relative path specified in the configuration, defaulting to "postProcessing/sidePod/0/sidePod.dat" if no specific file path is provided in the configuration

        # Read the file (whitespace-delimited, skip comment lines)
        df = pd.read_csv(
            file_path,
            sep=r"\s+",
            comment="#",
            header=None,
            engine="python"
        )
        # first two rows are commented, left column is time and right column is mass flow, we want to plot mass flow vs time
        df.columns = ["Time", "MassFlow"] # Assign column names to the DataFrame for easier access
        output_paths = []
        # Plot mass flow vs time
        plt.figure(figsize=(6, 4))
        plt.plot(df["Time"], df["MassFlow"]*self.rho, color="#2B6413")
        plt.title("Sidepod Area-Averaged Mass-flow rate vs Time")
        plt.xlabel("Time [s]")
        plt.ylabel("Mass-flow rate [kg/s]")
        plt.grid(axis="y", linestyle="-", alpha=0.5)

        # Save figure
        plt.tight_layout()
        output_path = self.out_dir / "sidepod_massflow_time.png"
        plt.savefig(output_path, dpi=150)
        plt.close()  # Close the figure to free memory
        self.log(f"Saved mass flow plot to {output_path}")
        output_paths.append(output_path)

        return output_paths