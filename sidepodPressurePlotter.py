from __future__ import annotations #fix issues with forward references in type hints (DelftBlue PVbatch is old)
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from base import PostStage

class SidePodPressurePlotter(PostStage): #Class object that inherits from the PostStage base class, responsible for generating pressure plots inside sidepods from OpenFOAM simulation data
    name = "sidePodPressure"
    
    def run(self) -> list[Path]:
        cfg = self.config.get("sidePodPressure", {}) # retrieves the configuration settings for the side pod pressure plotter from the overall configuration dictionary, using "sidePodPressure" as the key, and defaults to an empty dictionary if no specific settings are found
        file_path = self.case_dir / cfg.get("file", "postProcessing/probes/0/p") # constructs the file path to the side pod data file by combining the case directory with the relative path specified in the configuration, defaulting to "postProcessing/sidePod/0/sidePod.dat" if no specific file path is provided in the configuration

        # Read the file (whitespace-delimited, skip comment lines)
        df = pd.read_csv(
            file_path,
            sep=r"\s+",
            comment="#",
            header=None,
            engine="python"
        )
        # first two rows are commented, left column is time and right column is pressure, we want to plot pressure vs time
        df.columns = ["Time", "Pressure"] # Assign column names to the DataFrame for easier access
        output_paths = []
        # Plot pressure vs time
        plt.figure(figsize=(6, 4))
        plt.plot(df["Time"], df["Pressure"], color="#4C72B0")
        plt.title("Sidepod Pressure vs Time")
        plt.xlabel("Time [s]")
        plt.ylabel("Pressure  [Pa]")
        plt.grid(axis="y", linestyle="-", alpha=0.5)

        # Save figure
        plt.tight_layout()
        output_path = self.out_dir / "sidepod_pressure_time.png"
        plt.savefig(output_path, dpi=150)
        plt.close()  # Close the figure to free memory
        self.log(f"Saved pressure plot to {output_path}")
        output_paths.append(output_path)

        return output_paths