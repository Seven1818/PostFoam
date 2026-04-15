from __future__ import annotations #fix issues with forward references in type hints (DelftBlue PVbatch is old)
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from base import PostStage

class YPlusPlotter(PostStage): #Class object that inherits from the PostStage base class, responsible for generating Y+ plots from OpenFOAM simulation data
    name = "yPlus"

    def run(self) -> list[Path]:
        cfg = self.config.get("yPlus", {}) # retrieves the configuration settings for the Y+ plotter from the overall configuration dictionary, using "yPlus" as the key, and defaults to an empty dictionary if no specific settings are found
        file_path = self.case_dir / cfg.get("file", "postProcessing/yPlus/0/yPlus.dat") # constructs the file path to the Y+ data file by combining the case directory with the relative path specified in the configuration, defaulting to "postProcessing/yPlus/0/yPlus.dat" if no specific file path is provided in the configuration

        # Read the .dat file (whitespace-delimited, skip comment lines)
        df = pd.read_csv(
            file_path,
            sep=r"\s+",
            comment="#",
            header=None,
            names=["Time", "patch", "min", "max", "average"],
            engine="python"
        )

        # Filter only the last time step  and patches of interest (car, FW, RW, FWHL, RWHL)
        last_time = df["Time"].max()
        df_last = df[(df["Time"] == last_time) & (df["patch"].isin(["car", "FW", "RW", "FWHL", "RWHL"]))]

        # Ensure we have data
        if df_last.empty:
            raise ValueError(f"No data found for Time={last_time} and patches car/FW.")

        output_paths = []
        # Plot for each patch separately
        for patch in ["car", "FW", "RW", "FWHL", "RWHL"]:
            row = df_last[df_last["patch"] == patch]
            if row.empty:
                print(f"No data for patch {patch} at Time={last_time}")
                continue

            values = row[["min", "max", "average"]].iloc[0]
            labels = ["min", "max", "average"]

            plt.figure(figsize=(6, 4))
            plt.bar(labels, values, color=["#4C72B0", "#55A868", "#C44E52"])
            plt.title(f"Y+ stats for {patch} at Time={last_time}")
            plt.ylabel("Y+")
            plt.grid(axis="y", linestyle="--", alpha=0.5)

            # Save figure
            plt.tight_layout()
            output_path = self.out_dir / f"yplus_{patch}_time_{last_time}.png"
            plt.savefig(output_path, dpi=150)
            plt.close()  # Close the figure to free memory
            self.log(f"Saved Y+ plot for {patch} to {output_path}")
            output_paths.append(output_path)

        return output_paths
