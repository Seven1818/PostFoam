#!/usr/bin/env python3
"""
Render a ParaView state (.py) to PNG in batch mode.
Handles PV 5.11 → 5.9 compatibility and auto-fixes mesh region naming.
"""
import os
import re
import argparse
from paraview.simple import *

paraview.simple._DisableFirstRenderCameraReset() #Prevents ParaView from automatically resetting the camera to a default view

# ── Regions that are NOT car-surface patches ──
BOUNDARY_REGIONS = {
    'internalMesh', 'frontAndBack', 'inlet', 'outlet',
    'lowerWall', 'upperWall',
}

# Pressure colour map (diverging blue-white-red)
P_COLORMAP = [
    -6000.0, 0.231373, 0.298039, 0.752941,
    -1500.0, 0.865003, 0.865003, 0.865003,
     3000.0, 0.705882, 0.0156863, 0.14902,
]


def patch_state_for_pv59(state_text: str, foam_path: str) -> str:
    """Rewrite a PV 5.11 state script to run on PV 5.9.""" # Done in case users have an older PV version

    # Point all .foam readers at the current case
    state_text = re.sub(
        r"(FileName\s*=\s*)(['\"])(.*?\.foam)\2",
        rf"\1'{foam_path}'",
        state_text,
    )

    clean = [] # List to hold the cleaned lines of the state script after processing
    skip_tail = False
    for line in state_text.splitlines():
        s = line.strip()

        # Drop the if-__main__ / SaveExtracts tail
        if s.startswith("if __name__"):
            skip_tail = True
            continue
        if "SaveExtracts(" in line:
            continue
        if skip_tail and (s == "" or s.startswith("#")):
            continue
        skip_tail = False

        # Drop APIs that don't exist in PV 5.9
        if any(tok in line for tok in (
            "GetTransferFunction2D(", "TransferFunction2D",
            "uTF2D.", "pTF2D.",
            ".SelectInputVectors", ".WriteLog", ".WindowLocation",
        )):
            continue

        clean.append(line)

    return "\n".join(clean) + "\n"


def fix_mesh_regions(reader):
    """
    Returns the cell count after the fix attempt.
    """
    if reader.GetDataInformation().GetNumberOfCells() > 0: #If the reader already loaded cells successfully, do nothing. This is the happy path, the state file's region names already matched.
        return reader.GetDataInformation().GetNumberOfCells()

    avail = reader.GetProperty("MeshRegions").GetAvailable() # gets all available regions from the OpenFOAM mesh

    # 1) Explicit unprefixed surface names (PV 5.9)
    candidates = [r for r in avail
                  if r in ('car', 'FW', 'FWHL', 'RW', 'RWHL')]
    # 2) Everything that isn't a boundary or a patch/ duplicate
    if not candidates:
        candidates = [r for r in avail
                      if r not in BOUNDARY_REGIONS
                      and not r.startswith("patch/")]
    # 3) patch/ prefixed (PV 5.11)
    if not candidates:
        candidates = [r for r in avail if r.startswith("patch/")]

    if candidates:
        reader.MeshRegions = candidates
        reader.UpdatePipeline()

    return reader.GetDataInformation().GetNumberOfCells()


def render_state(state_py, case_dir, foam_file="Results_V1.foam",
                 out_png=None, width=1920, height=1080):
    """Main entry point – can be called from a larger post-processor.""" #takes the file path, case, directory and optional output settings

    case_dir = os.path.abspath(case_dir)
    foam_path = os.path.join(case_dir, foam_file)

    if out_png is None:
        out_dir = os.path.join(case_dir, "postProcessing", "images") #if no output path was given defatult to case/postProcessing/images/state_view.png
        os.makedirs(out_dir, exist_ok=True)
        out_png = os.path.join(out_dir, "state_view.png")
    else:
        out_png = os.path.abspath(out_png)
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)

    if not os.path.isfile(state_py): # error messages if the files don't exist
        raise FileNotFoundError(f"State file not found: {state_py}")
    if not os.path.isfile(foam_path):
        raise FileNotFoundError(f"FOAM file not found: {foam_path}")

    # Read & patch state
    with open(state_py, "r", encoding="utf-8") as f: # read the file and patch it for compatibility
        state_text = f.read()
    state_text = patch_state_for_pv59(state_text, foam_path)

    # Execute patched state
    exec(state_text, globals().copy()) # exectutes the patched state script as Python code, by using all paraview.simple functions and classes 

    # Grab view & advance to last timestep
    view = GetActiveViewOrCreate("RenderView") # Gets the active view from the state file, or creates a new RenderView if none exists
    scene = GetAnimationScene() 
    scene.UpdateAnimationUsingDataTimeSteps() # Reads all available timesteps form the data
    try: # to handle steady state case with only 1 timestep
        scene.GoToLast()
    except Exception:
        pass

    # Update all pipelines from state file (named in the state file as car_surface_foam, internal_mesh_foam, StreamTracer1, StreamTracer2)
    for name in ["car_surface_foam", "internal_mesh_foam",
                 "StreamTracer1", "StreamTracer2"]:
        src = FindSource(name)
        if src is not None:
            src.UpdatePipeline() #makes sure the data is actually loaded at the current timestep

    # Fix car surface regions if needed & show with pressure colouring
    car = FindSource("car_surface_foam")
    if car is not None:
        fix_mesh_regions(car)
        disp = Show(car, view)
        disp.Representation = 'Surface'
        disp.Opacity = 1.0
        ColorBy(disp, ('POINTS', 'p')) #colours the surface by pressure
        pLUT = GetColorTransferFunction('p')
        pLUT.AutomaticRescaleRangeMode = 'Never' #disables automatic rescaling
        pLUT.RGBPoints = P_COLORMAP #uses scaling from ColoroMap
        disp.LookupTable = pLUT

    # Hide raw internal mesh (streamtracers are separate objects)
    internal = FindSource("internal_mesh_foam")
    if internal is not None:
        Hide(internal, view)

    Render() # renders the view and saves it as a PNG at the the specified resolution
    SaveScreenshot(out_png, view, ImageResolution=[width, height])
    print(f"[OK] Screenshot saved: {out_png}")
    return out_png


# ── CLI wrapper ──
def main(): #Sets up command-line arguments. Each one falls back to an environment variable if not provided on the command line
    parser = argparse.ArgumentParser(
        description="Render a ParaView state to PNG in batch mode.")
    parser.add_argument("--state-py",  default=os.environ.get("STATE_PY"))
    parser.add_argument("--case-dir",  default=os.environ.get("CASE_DIR", os.getcwd()))
    parser.add_argument("--foam-file", default=os.environ.get("FOAM_FILE", "Results_V1.foam"))
    parser.add_argument("--out-png",   default=os.environ.get("OUT_PNG"))
    parser.add_argument("--width",  type=int, default=int(os.environ.get("IMG_WIDTH",  "1920")))
    parser.add_argument("--height", type=int, default=int(os.environ.get("IMG_HEIGHT", "1080")))
    args, _ = parser.parse_known_args() # ignores any extra arguments that pvbatch might reject

    if not args.state_py:
        raise RuntimeError("Provide --state-py or set STATE_PY env var.")

    render_state(
        state_py=args.state_py,
        case_dir=args.case_dir,
        foam_file=args.foam_file,
        out_png=args.out_png,
        width=args.width,
        height=args.height,
    )


if __name__ == "__main__":
    main()