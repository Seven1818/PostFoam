from __future__ import annotations #fix issues with forward references in type hints (DelftBlue PVbatch is old)
"""
plot_residuals.py  –  CFD residual convergence plot
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from base import PostStage

class ResidualsPlotter(PostStage): # Class object that inherits from the PostStage base class, responsible for generating a residual convergence plot from OpenFOAM simulation data, similar in style to Fluent's residual plots
    name = "residuals" # Class attribute that serves as a human-readable label for the stage, used in logs and the PDF report to identify the stage being executed

    def run(self) -> list[Path]:
        cfg = self.config.get("residuals", {}) # retrieves the configuration settings for the residuals plotter from the overall configuration dictionary, using "residuals" as the key, and defaults to an empty dictionary if no specific settings are found
        file_path = self.case_dir / cfg.get("file", "postProcessing/residuals/0/residuals.dat")
        light_mode = cfg.get("light_mode", False)

        fig = plot_residuals(file_path, light=light_mode) 

        output_path = self.out_dir / "residuals_plot.png" # constructs the output file path for the residuals plot
        fig.savefig(output_path, dpi=150) #saves the generated plot with a resoution of 150DPI
        plt.close(fig)  # Close the figure to free memory
        self.log(f"Saved residuals plot to {output_path}") # Output log message
        return [output_path]
    


COLOURS = ["#E63946","#2196F3","#4CAF50","#FF9800","#9C27B0","#00BCD4","#F06292","#FFEB3B"] # Define colours for the plot lines
LINESTYLES = ["-", "--", "-.", ":",(0, (1, 10)), (0, (3, 1, 1, 1, 1, 1))] # Define various line styles for better readeability in case of B&W printing

def read_residuals(filepath): # Function to read the residuals data and extract it
    variables, rows = [], []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if "Time" in line:
                    variables = line.lstrip("# ").split()[1:]
                continue
            line = line.replace("N/A", "nan")
            try:
                values = [float(x) for x in line.split()]
            except ValueError:
                continue
            rows.append(values)

    # Pad all rows to the same length (n_variables + 1 for the iteration column)
    n_cols = len(variables) + 1 # Calculate the expected number of columns based on the number of variables plus one for the iteration column
    padded = [row + [float("nan")] * (n_cols - len(row)) for row in rows] # Pad each row with NaN values to ensure all rows have the same number of columns, which is necessary for creating a consistent 2D array for plotting, especially when some variables may not be present in all iterations

    arr = np.array(padded) # Convert the list of padded rows into a NumPy array for easier manipulation and plotting
    iterations = arr[:, 0] # Extract the first column of the array as the iterations, which represents the iteration number for each data point
    data = arr[:, 1:n_cols] # Extract the columns corresponding to the variables (residuals) from the array, which will be used for plotting the residual convergence curves, while ignoring any extra columns that may have been added due to padding

    # Drop columns that are entirely NaN 
    valid_cols = ~np.all(np.isnan(data), axis=0)
    variables = [v for v, keep in zip(variables, valid_cols) if keep]
    data = data[:, valid_cols]

    return iterations, variables, data


def plot_residuals(filepath, light=False): # Function to create a residual convergence plot from the data read from the specified file path
    iterations, variables, data = read_residuals(filepath)

    bg, fg, grid = ("#1C1C2E", "#E0E0E0", "#2E2E4E") if not light else ("white", "#111111", "#DDDDDD") #Set background, foreground and grid colours

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor(bg); ax.set_facecolor(bg) # Set the background color of the figure and axes to the defined background color

    for i, var in enumerate(variables): # Loop through each variable (residual) and plot it on the axes using a semilogarithmic scale for the y-axis
        ax.semilogy(iterations, data[:, i],
                color=COLOURS[i % len(COLOURS)],
                linestyle=LINESTYLES[i % len(LINESTYLES)],   
                linewidth=1.6, label=f"${var}$", alpha=0.92)

    ax.set_xlabel("Iteration", fontsize=24, color=fg, labelpad=8)
    ax.set_ylabel("Residual",  fontsize=24, color=fg, labelpad=8)
    ax.set_title("Residual Convergence", fontsize=30, color=fg, fontweight="bold", pad=12)
    ax.set_xlim(left=iterations[0])
    ax.grid(True, which="major", color=grid, linewidth=0.7)
    ax.grid(True, which="minor", color=grid, linewidth=0.3, linestyle=":")
    ax.tick_params(colors=fg, which="both", labelsize=24)
    ax.yaxis.set_major_formatter(ticker.LogFormatterSciNotation())
    for spine in ax.spines.values(): spine.set_edgecolor("#444466" if not light else "#AAAAAA")
    ax.legend(fontsize=16, framealpha=0.85, facecolor="#16162A" if not light else "white",
              edgecolor=fg, labelcolor=fg, loc="upper right")
    plt.tight_layout()
    return fig


