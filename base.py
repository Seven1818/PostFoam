from __future__ import annotations #fix issues with forward references in type hints (DelftBlue PVbatch is old)
"""
base.py – Abstract base class for all post-processing stages.
Every stage receives the resolved config and returns a list of
Paths it produced. The orchestrator uses that list to build the report.
"""
from abc import ABC, abstractmethod
from pathlib import Path


class PostStage(ABC): #Abstract base class for all post-processing stages, defines the structure and interface that all specific post-processing stages must follow, ensuring consistency and modularity in the implementation of different stages of the post-processing workflow
    """
    Subclass this for every post-processing stage.

    Attributes
    ----------
    name : str
        Human-readable label used in logs and the PDF report.
    """

    name: str = "unnamed_stage" # Class attribute that serves as a human-readable label for the stage, used in logs and the PDF report to identify the stage being executed

    def __init__(self, case_dir: Path, out_dir: Path, config: dict):
        self.case_dir = Path(case_dir)
        self.out_dir = Path(out_dir)
        self.config = config
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def run(self) -> list[Path]:
        """
        Execute the stage and return a list of generated file paths
        (PNG images, CSVs, …) that the report assembler should include.
        """

    def log(self, msg: str):
        print(f"  [{self.name}] {msg}")
