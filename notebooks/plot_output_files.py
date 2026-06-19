"""Interactive quick-look plots for the Thetis gridded Level 2 product.

Each Level 2 file (``data/Level2/L2_THETIS_GRID_*.nc``) is a 10-day depth x time
grid. A full year spans many files, so they are concatenated along ``time`` into
one continuous record before plotting. Variables are either:
  - scalar     on ``(depth, time)``      -- temperature, oxygen, chla, ...
  - spectral   on ``(wavelength, time)`` -- Ed0, Lu0, kd_Ed, Rrs.

Run ``conda activate pipeline`` first so xarray/netCDF4 are available, then::

    python notebooks/plot_output_files.py --year 2023        # one calendar year
    python notebooks/plot_output_files.py --start 2023-04-01 --end 2023-10-01
    python notebooks/plot_output_files.py                    # all available data
    python notebooks/plot_output_files.py --list-years       # show what's available

The figures open in interactive matplotlib windows (pan/zoom/save).
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
L2_DIR = ROOT / "data" / "Level2"

_DATE_RE = re.compile(r"L2_THETIS_GRID_(\d{8})_(\d{8})\.nc$")


def file_span(path):
    """(start, end) datetimes parsed from a L2 filename."""
    m = _DATE_RE.search(path.name)
    if not m:
        return None, None
    return datetime.strptime(m.group(1), "%Y%m%d"), datetime.strptime(m.group(2), "%Y%m%d")


def list_files(start=None, end=None):
    """L2 files whose 10-day span overlaps [start, end], sorted by date."""
    files = sorted(L2_DIR.glob("L2_THETIS_GRID_*.nc"))
    if start is None and end is None:
        return files
    keep = []
    for f in files:
        fstart, fend = file_span(f)
        if fstart is None:
            continue
        if start is not None and fend < start:
            continue
        if end is not None and fstart > end:
            continue
        keep.append(f)
    return keep


def load_period(start=None, end=None):
    """Open and concatenate L2 files into a single time-sorted dataset."""
    files = list_files(start, end)
    if not files:
        raise SystemExit("No Level 2 files found for the requested period.")
    print(f"Loading {len(files)} file(s)...")
    ds = xr.open_mfdataset(
        files,
        combine="nested",
        concat_dim="time",
        # depth/wavelength grids are identical across files; keep coords from the first.
        coords="minimal",
        compat="override",
    )
    ds = ds.sortby("time")
    if start is not None or end is not None:
        ds = ds.sel(time=slice(start, end))
    return ds


def label(ds, var):
    """Human-readable axis label from CF attributes."""
    attrs = ds[var].attrs
    name = attrs.get("long_name", var)
    units = attrs.get("units", "")
    return f"{name} [{units}]" if units else name


def _format_time_axis(ax):
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))


def plot_depth_time(ds, title):
    """Heatmaps for every ``(depth, time)`` variable."""
    variables = [v for v in ds.data_vars if set(ds[v].dims) == {"depth", "time"}]
    if not variables:
        return
    ncols = 3
    nrows = int(np.ceil(len(variables) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3 * nrows), squeeze=False)
    for ax, var in zip(axes.flat, variables):
        da = ds[var]
        vmin, vmax = np.nanpercentile(da.values, [2, 98])  # robust to outliers
        mesh = ax.pcolormesh(
            ds["time"], ds["depth"], da, shading="nearest", vmin=vmin, vmax=vmax, cmap="viridis"
        )
        ax.invert_yaxis()  # depth increases downward
        ax.set_title(label(ds, var), fontsize=9)
        ax.set_ylabel("depth [m]")
        _format_time_axis(ax)
        fig.colorbar(mesh, ax=ax)
    for ax in axes.flat[len(variables):]:
        ax.set_visible(False)
    fig.suptitle(title, y=1.005)
    fig.tight_layout()


def plot_spectral_time(ds, title):
    """Heatmaps for every ``(wavelength, time)`` variable."""
    variables = [v for v in ds.data_vars if set(ds[v].dims) == {"wavelength", "time"}]
    if not variables:
        return
    ncols = 2
    nrows = int(np.ceil(len(variables) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.2 * nrows), squeeze=False)
    for ax, var in zip(axes.flat, variables):
        da = ds[var]
        vmin, vmax = np.nanpercentile(da.values, [2, 98])
        mesh = ax.pcolormesh(
            ds["time"], ds["wavelength"], da, shading="nearest", vmin=vmin, vmax=vmax, cmap="turbo"
        )
        ax.set_title(label(ds, var), fontsize=9)
        ax.set_ylabel("wavelength [nm]")
        _format_time_axis(ax)
        fig.colorbar(mesh, ax=ax)
    for ax in axes.flat[len(variables):]:
        ax.set_visible(False)
    fig.suptitle(title, y=1.005)
    fig.tight_layout()


def list_years():
    """Print the years covered by the available L2 files and their counts."""
    counts = {}
    for f in list_files():
        fstart, _ = file_span(f)
        if fstart is not None:
            counts[fstart.year] = counts.get(fstart.year, 0) + 1
    for year in sorted(counts):
        print(f"{year}: {counts[year]:3d} files")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--year", type=int, help="Plot a single calendar year, e.g. 2023")
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--list-years", action="store_true", help="List years with data and exit")
    args = parser.parse_args()

    if args.list_years:
        list_years()
        return

    if args.year is not None:
        start = pd.Timestamp(args.year, 1, 1)
        end = pd.Timestamp(args.year, 12, 31, 23, 59, 59)
        title = f"Thetis L2 — {args.year}"
    else:
        start = pd.Timestamp(args.start) if args.start else None
        end = pd.Timestamp(args.end) if args.end else None
        span = f"{args.start or 'start'} to {args.end or 'end'}"
        title = f"Thetis L2 — {span}"

    ds = load_period(start, end)
    print(f"Time range: {ds['time'].min().values} to {ds['time'].max().values} "
          f"({ds.sizes['time']} casts)")

    plot_depth_time(ds, title)
    plot_spectral_time(ds, title)
    plt.show()


if __name__ == "__main__":
    main()
