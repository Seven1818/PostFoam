from __future__ import annotations #fix issues with forward references in type hints (DelftBlue PVbatch is old)
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from base import PostStage

class Cl_plotter(PostStage): #Class object that inherits from the PostStage base class, responsible for generating Lift coefficient plots from the OpenFOAM forceCoeffs function 
    name = "Cl"
    
    def run(self) -> list[Path]:
        cfg = self.config.get("Cl", {})  # retrieves the configuration settings for the lift coefficient plotter from the overall configuration dictionary, using "Cl" as the key, and defaults to an empty dictionary if no specific settings are found
        file_path = self.case_dir / cfg.get("file", "postProcessing/forceCoeffs/0/forceCoeffs.dat") # constructs the file path to the side pod data file by combining the case directory with the relative path specified in the configuration, defaulting to "postProcessing/forceCoeffs/0/forceCoeffs.dat" if no specific file path is provided in the configuration
        # Read the file (whitespace-delimited, skip comment lines)
        df = pd.read_csv(
            file_path,
            sep=r"\s+",
            comment="#",
            header=None,
            engine="python"
        )
        # first 9 rows are commented, left column is time and  3rd column is Cd, we want to plot Cd vs time
        df.columns = ["Time","Cm", "Cd", "Cl","Cl_f","Cl_r"] # Assign column names to the DataFrame for easier access
        output_paths = []
        # Plot Cl vs time
        plt.figure(figsize=(6, 4))
        plt.plot(df["Time"], df["Cl"], color="#B0584C")
        plt.title("Lift Coefficient vs Time")
        plt.xlabel("Time [s]")
        plt.ylabel("Lift Coefficient")
        plt.grid(axis="y", linestyle="-", alpha=0.5)

        # Save figure
        plt.tight_layout()
        output_path = self.out_dir / "cl_time.png"
        plt.savefig(output_path, dpi=150)
        plt.close()  # Close the figure to free memory
        self.log(f"Saved lift coefficient plot to {output_path}")
        output_paths.append(output_path)

        return output_paths