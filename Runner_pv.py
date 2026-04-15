from PostProcesser import render_state


def main():
    render_state(
        state_py="State_1.py",
        case_dir="./",
        foam_file="Results_V2_half.foam",
        out_png="./postProcessing/images/foam_render.png",
        width=1920,
        height=1080,
    )

if __name__ == "__main__":
    main()