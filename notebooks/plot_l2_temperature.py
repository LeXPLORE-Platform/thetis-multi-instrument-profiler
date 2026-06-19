"""Plot the full Thetis L2 temperature record as a depth-time heatmap.

Concatenates every ``data/Level2/L2_THETIS_GRID_*.nc`` file along time and plots
the temperature field across the whole deployment (2018-present).

Run ``conda activate pipeline`` first, then::

    python notebooks/plot_l2_temperature.py            # interactive window
    python notebooks/plot_l2_temperature.py -o temp.png # save to file instead
"""

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
L2_DIR = ROOT / "data" / "Level2"


def load_temperature():
    """Open all L2 files and return a time-sorted (depth, time) temperature array."""
    files = sorted(L2_DIR.glob("L2_THETIS_GRID_*.nc"))
    if not files:
        raise SystemExit(f"No Level 2 files found in {L2_DIR}")
    print(f"Loading temperature from {len(files)} files...")
    ds = xr.open_mfdataset(
        files,
        combine="nested",
        concat_dim="time",
        coords="minimal",
        compat="override",
        data_vars=["temp"],  # only read what we plot
    )
    temp = ds["temp"].sortby("time")
    return temp.load()  # force the read so timing/progress is up front


def gapped_time_mesh(ax, times, depth, values, max_hours=12, **kw):
    """pcolormesh whose cells are capped at ``max_hours`` wide.

    With ``shading="nearest"`` each cast would stretch halfway to its neighbour,
    smearing isolated profiles across data gaps. Here every cell is at most
    ``max_hours`` wide (centred on the cast) and gaps are filled with NaN cells
    so they render blank.
    """
    tnum = mdates.date2num(times)
    half = max_hours / 24.0 / 2.0  # half cell width, in days
    n = len(tnum)
    left = np.empty(n)
    right = np.empty(n)
    if n > 1:
        d = np.diff(tnum)
        left[1:] = tnum[1:] - np.minimum(d / 2, half)
        right[:-1] = tnum[:-1] + np.minimum(d / 2, half)
    left[0] = tnum[0] - half
    right[-1] = tnum[-1] + half

    # Build contiguous cell boundaries, inserting a NaN cell wherever a gap opens.
    boundaries = [left[0]]
    cols = []
    nan_col = np.full(values.shape[0], np.nan)
    for i in range(n):
        cols.append(values[:, i])
        boundaries.append(right[i])
        if i < n - 1 and left[i + 1] > right[i]:
            cols.append(nan_col)
            boundaries.append(left[i + 1])
    x_edges = mdates.num2date(np.array(boundaries))
    c = np.column_stack(cols)

    # Cell edges for the (regular) depth axis.
    dd = np.diff(depth)
    y_edges = np.concatenate([[depth[0] - dd[0] / 2], depth[:-1] + dd / 2, [depth[-1] + dd[-1] / 2]])

    return ax.pcolormesh(x_edges, y_edges, c, shading="flat", **kw)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", type=Path, help="Save figure to this path instead of showing it")
    args = parser.parse_args()

    temp = load_temperature()
    t0 = np.datetime_as_string(temp["time"].min().values, unit="D")
    t1 = np.datetime_as_string(temp["time"].max().values, unit="D")
    print(f"{temp.sizes['time']} casts from {t0} to {t1}")

    vmin, vmax = np.nanpercentile(temp.values, [1, 99])  # robust colour limits
    fig, ax = plt.subplots(figsize=(16, 5))
    mesh = gapped_time_mesh(
        ax, temp["time"].values, temp["depth"].values, temp.values,
        max_hours=12, cmap="turbo", vmin=vmin, vmax=vmax,
    )
    ax.invert_yaxis()  # depth increases downward
    ax.set_ylabel("depth [m]")
    ax.set_title(f"Thetis L2 temperature  ({t0} to {t1})")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label(f"temperature [{temp.attrs.get('units', 'degC')}]")
    fig.tight_layout()

    if args.output:
        fig.savefig(args.output, dpi=150)
        print(f"Saved {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
