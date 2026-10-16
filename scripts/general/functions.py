# -*- coding: utf-8 -*-
import io
import os
import re
import csv
import pytz
import copy
import json
import netCDF4
import traceback
import numpy as np
import pandas as pd
from envass import qualityassurance
from math import sin, cos, sqrt, atan2, radians
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt


class GenericInstrument:
    def __init__(self, log=False):
        self.general_attributes = {
            "institution": "",
            "source": "",
            "references": "",
            "history": "",
            "conventions": "CF 1.7",
            "comment": "",
            "title": ""
        }
        self.dimensions = {}
        self.variables = {}
        self.data = {}
        self.grid = {}
        if log != False:
            self.log = log
        else:
            self.log = logger()

    def quality_assurance(self, file_path='./quality_assurance.json', valid=False, time_label="time"):
        self.log.info("Applying quality assurance", indent=2)

        if not os.path.exists(file_path):
            self.log.warning("Cannot find QA file: {}, no QA applied.".format(file_path), indent=2)
            return False

        quality_assurance_dict = json_converter(json.load(open(file_path)))
        for key, values in self.variables.copy().items():
            if "_qual" not in key and key in quality_assurance_dict:
                name = key + "_qual"
                self.variables[name] = {'var_name': name, 'dim': values["dim"],
                                        'unit': '0 = nothing to report, 1 = more investigation',
                                        'long_name': name, }
                if len(self.data[key]) == 1:
                    self.data[name] = np.array([1])
                else:
                    on_time_axis = time_label in values["dim"]
                    if on_time_axis:
                        reference = np.array(self.data[time_label])
                    else:
                        # Variable is not indexed by time (e.g. wavelength-indexed
                        # OCR products). envass only uses the second argument for a
                        # length check on numeric/bounds tests, so pass a matching-
                        # length reference axis to avoid a spurious length mismatch.
                        reference = np.arange(len(self.data[key]))
                    qa = qualityassurance(np.array(self.data[key]), reference,
                                          **quality_assurance_dict[key]["simple"])
                    if valid and on_time_axis:
                        time = np.array(self.data[time_label])
                        if min(time) < valid[0] < max(time) and min(time) < valid[1] < max(time):
                            qa[time < valid[0]] = 1
                            qa[time > valid[1]] = 1
                    self.data[name] = np.array(qa)

    def apply_events(self, events_file, time_label="time", depth_label="depth", flag=1, profile=False,
                     owners=None, instrument=None, shared=False):
        """Set flag in the _qual variables for every event in events_file that overlaps this data.
        With profile=True the data is a single profile: an event that overlaps it in time applies to the whole
        profile, and only its depth spec limits which points are flagged.
        With shared=True the events file is shared between instruments: "All" rows apply to every instrument and
        named parameters only to the instrument that owns them in owners.
        Problems with the events file are logged as warnings and never stop processing."""
        self.log.info("Applying events from {}".format(events_file), indent=2)
        try:
            if not os.path.exists(events_file):
                self.log.warning("Cannot find events file: {}, no events applied.".format(events_file), indent=2)
                return False
            events = parse_events(events_file, self.log)
            if events is None:
                return False

            time = np.array(self.data[time_label], dtype=float)
            depths = np.array(self.data[depth_label], dtype=float) if depth_label in self.data else None
            # Per-sample depths are matched at the resolution of the Level 2 grid, a depth dimension at its own spacing
            grid = getattr(self, "grid_depths", None) if depth_label not in self.dimensions else None
            tol = depth_tolerance(grid, depths)
            propagation = getattr(self, "event_propagation", {})
            events = [e for e in events if e["start"] <= np.nanmax(time) and e["stop"] >= np.nanmin(time)]
            if not events:
                self.log.info("No events overlap this data.", indent=3)
        except Exception as e:
            self.log.warning("Unable to apply events from {} ({}: {}), no events applied.".format(
                events_file, type(e).__name__, e), indent=2)
            return False

        for event in events:
            try:
                self.apply_event(event, time, depths, tol, propagation, time_label, depth_label, flag, profile,
                                 owners if shared else None, instrument, owners)
            except Exception as e:
                self.log.warning("Unable to apply event on line {} ({}: {}), skipped.".format(
                    event["line"], type(e).__name__, e), indent=3)
        return True

    def apply_event(self, event, time, depths, tol, propagation, time_label, depth_label, flag, profile=False,
                    routing=None, instrument=None, owners=None):
        line = event["line"]
        variables = event_variables(event["parameter"], self.variables, time_label=time_label,
                                    owners=routing, instrument=instrument)
        if routing is not None and not variables["qual"]:
            self.log.info("Line {}: no parameter for {}, skipped.".format(line, instrument), indent=3)
            return
        self.log.info("Line {}: {} (parameter: {}, depth: {})".format(
            line, event["comments"], event["parameter"], event["depth"] or "All"), indent=3)

        for parameter in variables["unknown"]:
            if owners and parameter in owners and owners[parameter] != instrument:
                self.log.warning("Unknown parameter {} in events line {}, it belongs in events_{}.csv".format(
                    parameter, line, owners[parameter]), indent=4)
            else:
                self.log.warning("Unknown parameter {} in events line {}".format(parameter, line), indent=4)
        qual = list(variables["qual"])
        for name in variables["qual"]:
            added = [d + "_qual" for d in propagation.get(name[:-len("_qual")], [])
                     if d + "_qual" in self.variables and d + "_qual" not in qual]
            if added:
                self.log.info("{} also flags derived variables: {}".format(name, ", ".join(added)), indent=4)
                qual.extend(added)
        if not qual:
            self.log.warning("Event on line {} matches no variable, nothing flagged.".format(line), indent=4)
            return

        if profile:
            time_mask = np.ones(len(time), dtype=bool)
        else:
            time_mask = (time >= event["start"]) & (time <= event["stop"])
        if not time_mask.any():
            self.log.warning("Event on line {} falls in a gap in the data, nothing flagged.".format(line), indent=4)
            return

        # The axis that time and depth are measured along: "time" for per-sample depths, "depth" for a depth dimension
        axis = self.variables[time_label]["dim"][0]
        spec = event["depth"]
        if spec == "" or spec.lower() == "all":
            mask = time_mask
        else:
            if depths is None:
                self.log.warning("Event on line {} has depth {} but the data has no depth, skipped.".format(line, spec), indent=4)
                return
            unflagged = np.zeros(len(depths), dtype=bool)
            for name in qual:
                if axis in self.variables[name]["dim"]:
                    unflagged |= self.unflagged_points(name, axis)
            missing = int(np.sum(time_mask & np.isnan(depths) & unflagged))
            if missing:
                self.log.warning("{} unflagged points in the event on line {} have no depth and are not flagged by it.".format(missing, line), indent=4)
            items = parse_event_depths(spec, np.where(time_mask, depths, np.nan), self.log, line, tol)
            if items is None:
                return
            mask = np.logical_or.reduce([m for m, _, _ in items])
            if not mask.any():
                self.log.warning("Event on line {} matches no depth in the data, nothing flagged.".format(line), indent=4)
                return

        for name in qual:
            values = np.array(self.data[name])
            dims = self.variables[name]["dim"]
            if axis in dims:
                index = np.ix_(*[mask if d == axis else np.arange(values.shape[i]) for i, d in enumerate(dims)])
            else:
                if spec != "" and spec.lower() != "all":
                    self.log.info("{} has no {} axis, depth {} ignored.".format(name, axis, spec), indent=4)
                index = (Ellipsis,)
            values[index] = np.bitwise_or(values[index].astype(int), flag)
            self.data[name] = values
        self.log.info("Flagged {} points for {}".format(int(mask.sum()), ", ".join(qual)), indent=4)

    def unflagged_points(self, name, axis):
        """Points along axis where the _qual variable name is still 0 for at least one value."""
        values = np.array(self.data[name])
        dims = self.variables[name]["dim"]
        values = np.moveaxis(values, dims.index(axis), 0)
        return (values.reshape(values.shape[0], -1) == 0).any(axis=1)

    def mask_outside_water_and_upcast_ctd(self, rolling=3, diff=0.01, var="Cond", depth="Press", max_depth_cut=3.0):
        self.log.info("Masking data from outside water and the upcast.", 2)
        bottom_of_profile_index = np.argmax(np.array(self.data[depth]))
        df = pd.DataFrame(np.array(self.data[var]))
        df_mean = df.rolling(rolling, center=True).mean().bfill().ffill()
        df_diff = df_mean.diff()
        outliers = np.array(np.abs(df_diff) > diff).flatten()
        water_entry_index = np.where(outliers[:np.argmax(np.array(self.data[depth]) > max_depth_cut)])[0][-1]

        for key, values in self.variables.copy().items():
            if "_qual" in key and "time" not in key and "Press" not in key:
                self.data[key][bottom_of_profile_index:] = 1
                self.data[key][:water_entry_index] = 1

    def export(self, folder, title, output_period="file", time_label="time", profile_to_grid=False, overwrite=False):
        if profile_to_grid:
            variables = self.grid_variables
            dimensions = self.grid_dimensions
            data = self.grid
        else:
            variables = self.variables
            dimensions = self.dimensions
            data = self.data

        time = data[time_label]
        time_min = datetime.fromtimestamp(np.nanmin(time), tz=timezone.utc).replace(tzinfo=pytz.utc)
        time_max = datetime.fromtimestamp(np.nanmax(time), tz=timezone.utc).replace(tzinfo=pytz.utc)
        if output_period == "file":
            file_start = time_min
            file_period = time_max - time_min
        elif output_period == "daily":
            file_start = (time_min - timedelta(days=time_min.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            file_period = timedelta(days=1)
        elif output_period == "weekly":
            file_start = (time_min - timedelta(days=time_min.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            file_period = timedelta(weeks=1)
        elif output_period == "monthly":
            file_start = time_min.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            file_period = relativedelta(months=+1)
        elif output_period == "yearly":
            file_start = time_min.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            file_period = relativedelta(year=+1)
        else:
            self.log.warning('Output period "{}" not recognised.'.format(output_period), indent=2)
            return

        if not os.path.exists(folder):
            os.makedirs(folder)

        output_files = []
        while file_start < time_max:
            file_end = file_start + file_period
            filename = "{}_{}.nc".format(title, file_start.strftime('%Y%m%d_%H%M%S'))
            out_file = os.path.join(folder, filename)
            output_files.append(out_file)
            self.log.info(
                "Writing {} data from {} until {} to NetCDF file {}".format(title, file_start, file_end, filename),
                indent=2)

            valid_time = (time >= datetime.timestamp(file_start)) & (time <= datetime.timestamp(file_end))

            if not os.path.isfile(out_file):
                self.log.info("Creating new file.", indent=3)
                with netCDF4.Dataset(out_file, mode='w', format='NETCDF4') as nc:
                    for key in self.general_attributes:
                        setattr(nc, key, self.general_attributes[key])
                    # Only the time axis is allowed to grow (it is the record
                    # axis appended to when files span multiple profiles); every
                    # other dimension gets its real size so HDF5 picks sane chunk
                    # shapes instead of huge default chunks that bloat the file.
                    for key, values in dimensions.items():
                        dim_name = values['dim_name']
                        if dim_name != time_label and dim_name in data and hasattr(data[dim_name], "__len__"):
                            dim_size = len(data[dim_name])
                        else:
                            dim_size = None
                        nc.createDimension(dim_name, dim_size)
                    for key, values in variables.items():
                        var = nc.createVariable(values["var_name"], np.float64, values["dim"], fill_value=np.nan, zlib=True, complevel=4)
                        var.units = values["unit"]
                        var.long_name = values["long_name"]
                        if profile_to_grid and key == time_label:
                            var[0] = time[0]
                        elif profile_to_grid and len(values["dim"]) == 2:
                            if values["dim"][0] == time_label:
                                var[0, :] = data[key]
                            elif values["dim"][1] == time_label:
                                var[:, 0] = data[key]
                            else:
                                raise ValueError("Failed to write variable {} with dimensions: {} to file".format(key, ", ".join(values["dim"])))
                        else:
                            if len(values["dim"]) == 1:
                                if values["dim"][0] == time_label:
                                    var[:] = data[key]
                                else:
                                    var[:] = data[key]
                            elif len(values["dim"]) == 2:
                                if values["dim"][0] == time_label:
                                    var[:] = data[key][valid_time, :]
                                elif values["dim"][1] == time_label:
                                    var[:] = data[key][:, valid_time]
                            else:
                                raise ValueError("Failed to write variable {} with dimensions: {} to file".format(key, ", ".join(values["dim"])))
            else:
                self.log.info("Editing existing file.", indent=3)
                with netCDF4.Dataset(out_file, mode='a', format='NETCDF4') as nc:
                    nc_time = np.array(nc.variables[time_label][:])
                    if profile_to_grid:
                        if time[0] in nc_time:
                            if overwrite:
                                self.log.info("Overwriting data at {}.".format(time[0]), indent=3)
                                idx = np.where(nc_time == time[0])[0][0]
                                for key, values in variables.items():
                                    if key not in dimensions:
                                        if len(values["dim"]) == 1:
                                            if hasattr(data[key], "__len__"):
                                                nc.variables[key][idx] = data[key][0]
                                            else:
                                                nc.variables[key][idx] = data[key]
                                        elif len(values["dim"]) == 2 and values["dim"][1] == time_label:
                                            nc.variables[key][:, idx] = data[key]
                                        else:
                                            self.log.warning("Unable to write {} with {} dimensions.".format(key, len(
                                                values["dim"])))

                            else:
                                self.log.info("Grid data already exists in NetCDF, skipping.", indent=3)
                        else:
                            idx = position_in_array(nc_time, time[0])
                            nc.variables[time_label][:] = np.insert(nc_time, idx, time[0])
                            for key, values in variables.items():
                                if key not in dimensions:
                                    var = nc.variables[key]
                                    if len(values["dim"]) == 1:
                                        if hasattr(data[key], "__len__"):
                                            var[idx] = data[key][0]
                                        else:
                                            var[idx] = data[key]
                                    elif len(values["dim"]) == 2 and values["dim"][1] == time_label:
                                        end = len(var[:][0]) - 1
                                        if idx != end:
                                            var[:, end] = data[key]
                                            var[:] = var[:, np.insert(np.arange(end), idx, end)]
                                        else:
                                            var[:, idx] = data[key]
                                    else:
                                        self.log.warning(
                                            "Unable to write {} with {} dimensions.".format(key, len(values["dim"])))
                    else:
                        if np.all(np.isin(time, nc_time)) and not overwrite:
                            self.log.info("Data already exists in NetCDF, skipping.", indent=3)
                        else:
                            non_duplicates = ~np.isin(time, nc_time)
                            valid = np.logical_and(valid_time, non_duplicates)
                            combined_time = np.append(nc_time, time[valid])
                            order = np.argsort(combined_time)
                            nc_copy = copy_variables(nc.variables)
                            for key, values in self.variables.items():
                                if time_label in values["dim"]:
                                    if len(values["dim"]) == 1:
                                        combined = np.append(nc_copy[key][:], np.array(data[key])[valid])
                                        if overwrite:
                                            combined[np.isin(combined_time, time)] = np.array(data[key])[
                                                np.isin(time, combined_time)]
                                        out = combined[order]
                                    elif len(values["dim"]) == 2 and values["dim"][1] == time_label:
                                        combined = np.concatenate((np.array(nc_copy[key][:]), np.array(data[key])[:, valid]), axis=1)
                                        if overwrite:
                                            combined[:, np.isin(combined_time, time)] = np.array(data[key])[:, np.isin(time, combined_time)]
                                        out = combined[:, order]
                                    else:
                                        raise ValueError(
                                            "Failed to write variable {} with dimensions: {} to file"
                                            .format(key, ", ".join(values["dim"])))
                                    nc.variables[key][:] = out
            file_start = file_start + file_period
        return output_files

    def mask_data(self):
        self.log.info("Masking L1 data.", indent=2)
        for var in self.variables:
            if var + "_qual" in self.data:
                idx = self.data[var + "_qual"][:] > 0
                self.data[var][idx] = np.nan

    def profile_to_timeseries_grid(self, time_label="time", depth_label="depth"):
        self.log.info("Resampling profile to fixed grid...", indent=2)
        try:
            self.grid[depth_label] = self.depths
        except:
            raise ValueError("self.depths must be defined as an fixed array of depths to produce timeseries grid.")
        self.grid[time_label] = np.array([self.data[time_label][0]])
        for key, values in self.grid_variables.items():
            if key not in self.grid_dimensions:
                if len(values["dim"]) == 1:
                    if "depth" in values and "source" in values:
                        mask = (~np.isnan(self.data[values["source"]])) & (~np.isnan(self.data[depth_label]))
                        pressures = self.data[depth_label][mask]
                        data = self.data[values["source"]][mask]
                        self.grid[key] = np.interp([float(values["depth"])], pressures, data, left=np.nan, right=np.nan)
                    else:
                        self.log.warning(
                            '"depth" and "source" keys must be included in self.variables["{}"].'.format(key), indent=2)
                elif len(values["dim"]) == 2:
                    mask = (~np.isnan(self.data[key])) & (~np.isnan(self.data[depth_label]))
                    pressures = self.data[depth_label][mask]
                    data = self.data[key][mask]
                    if len(data) < 5:
                        self.grid[key] = np.asarray([np.nan] * len(self.depths))
                    else:
                        self.grid[key] = np.interp(self.depths, pressures, data, left=np.nan, right=np.nan)
                else:
                    self.log.warning(
                        "Unable to process data for {} with {} dimensions.".format(key, len(values["dim"])), indent=2)

    def read_netcdf_data(self, file):
        with netCDF4.Dataset(file, 'r') as nc:
            for key in nc.variables.keys():
                self.data[key] = np.array(nc.variables[key][:])


class logger(object):
    def __init__(self, path=False, time=True):
        if path != False:
            if os.path.exists(os.path.dirname(path)):
                path.split(".")[0]
                if time:
                    self.path = "{}_{}.log".format(path.split(".")[0], datetime.now().strftime("%H%M%S.%f"))
                else:
                    self.path = "{}.log".format(path.split(".")[0])
            else:
                print("\033[93mUnable to find log folder: {}. Logs will be printed but not saved.\033[0m".format(
                    os.path.dirname(path)))
                self.path = False
        else:
            self.path = False
        self.stage = 1

    def info(self, string, indent=0):
        out = datetime.now().strftime("%H:%M:%S.%f") + (" " * 3 * (indent + 1)) + string
        print(out)
        if self.path:
            with open(self.path, "a") as file:
                file.write(out + "\n")

    def initialise(self, string):
        out = "****** " + string + " ******"
        print('\033[1m' + out + '\033[0m')
        if self.path:
            with open(self.path, "a") as file:
                file.write(out + "\n")

    def begin_stage(self, string):
        self.newline()
        out = datetime.now().strftime("%H:%M:%S.%f") + "   Stage {}: ".format(self.stage) + string
        self.stage = self.stage + 1
        print('\033[95m' + out + '\033[0m')
        if self.path:
            with open(self.path, "a") as file:
                file.write(out + "\n")
        return self.stage - 1

    def end_stage(self):
        out = datetime.now().strftime("%H:%M:%S.%f") + "   Stage {}: Completed.".format(self.stage - 1)
        print('\033[92m' + out + '\033[0m')
        if self.path:
            with open(self.path, "a") as file:
                file.write(out + "\n")

    def warning(self, string, indent=0):
        out = datetime.now().strftime("%H:%M:%S.%f") + (" " * 3 * (indent + 1)) + "WARNING: " + string
        print('\033[93m' + out + '\033[0m')
        if self.path:
            with open(self.path, "a") as file:
                file.write(out + "\n")

    def error(self):
        out = datetime.now().strftime("%H:%M:%S.%f") + "   ERROR: Script failed on stage {}".format(self.stage - 1)
        print('\033[91m' + out + '\033[0m')
        if self.path:
            with open(self.path, "a") as file:
                file.write(out + "\n")
                file.write("\n")
                traceback.print_exc(file=file)

    def end(self, string):
        out = "****** " + string + " ******"
        print('\033[92m' + out + '\033[0m')
        if self.path:
            with open(self.path, "a") as file:
                file.write(out + "\n")

    def subprocess(self, process, error=""):
        failed = False
        while True:
            output = process.stdout.readline()
            out = output.strip()
            print(out)
            if error != "" and error in out:
                failed = True
            if self.path:
                with open(self.path, "a") as file:
                    file.write(out + "\n")
            return_code = process.poll()
            if return_code is not None:
                for output in process.stdout.readlines():
                    out = output.strip()
                    print(out)
                    if self.path:
                        with open(self.path, "a") as file:
                            file.write(out + "\n")
                break
        return failed

    def newline(self):
        print("")
        if self.path:
            with open(self.path, "a") as file:
                file.write("\n")


EVENT_COLUMNS = ["start", "stop", "parameter", "depth", "comments"]


def parse_events(events_file, log):
    """Read an events file (start;stop;parameter;depth;comments) and return a list of events with start/stop as
    epoch seconds. An empty stop means the event is ongoing. Malformed rows are reported and skipped.
    Returns None if the file cannot be used at all."""
    try:
        try:
            with open(events_file, encoding="utf-8-sig", newline="") as f:
                text = f.read()
        except UnicodeDecodeError:
            log.warning("Events file {} is not UTF-8, reading it as Latin-1. Please save it as UTF-8.".format(events_file), indent=2)
            with open(events_file, encoding="latin-1", newline="") as f:
                text = f.read()
        reader = csv.reader(io.StringIO(text), delimiter=";")
        header = next(reader, None)
        if header is None:
            log.warning("Events file {} is empty, no events applied.".format(events_file), indent=2)
            return None
        header = [c.strip().lstrip("﻿").lower() for c in header]
        missing = [c for c in EVENT_COLUMNS if c not in header]
        if missing:
            log.warning("Events file {} missing columns: {}, no events applied.".format(events_file, ", ".join(missing)), indent=2)
            return None

        now = datetime.now(timezone.utc).timestamp()
        events = []
        for row in reader:
            line = reader.line_num
            if not any(c.strip() for c in row):
                continue
            if len(row) > len(header) and not any(c.strip() for c in row[len(header):]):
                row = row[:len(header)]
            if len(row) != len(header):
                log.warning("Invalid event on line {} of {} ({} fields, expected {}; quote comments containing ';'), skipped.".format(
                    line, events_file, len(row), len(header)), indent=3)
                continue
            event = {c: row[header.index(c)].strip() for c in EVENT_COLUMNS}
            start = parse_event_time(event["start"])
            stop = now if event["stop"] == "" else parse_event_time(event["stop"])
            if event["start"] == "":
                problem = "empty start"
            elif start is None:
                problem = "unable to parse start '{}'".format(event["start"])
            elif stop is None:
                problem = "unable to parse stop '{}'".format(event["stop"])
            elif stop < start:
                problem = "stop before start"
            elif event["parameter"] == "":
                problem = "empty parameter"
            else:
                event.update({"start": start, "stop": stop, "line": line})
                events.append(event)
                continue
            log.warning("Invalid event on line {} of {} ({}), skipped.".format(line, events_file, problem), indent=3)
        return events
    except Exception as e:
        log.warning("Unable to read events file {} ({}: {}), no events applied.".format(events_file, type(e).__name__, e), indent=2)
        return None


def parse_event_time(value):
    if not re.fullmatch(r"\d{8} \d{2}:\d{2}:\d{2}", value):
        return None
    try:
        return datetime.strptime(value, "%Y%m%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def event_parameters(parameter):
    return list(dict.fromkeys(p.strip() for p in parameter.split(",") if p.strip()))


def event_variables(parameter, variables, time_label="time", owners=None, instrument=None):
    """Map an events parameter ("All" or comma separated variable names) to the matching _qual variables.
    With owners (shared events file) only the parameters owned by instrument are kept, and the others are not
    reported as unknown (they are checked once per run by check_shared_events)."""
    qual = [k for k in variables if k.endswith("_qual") and k != time_label + "_qual"]
    if parameter.strip().lower() == "all":
        return {"qual": qual, "unknown": []}
    names = event_parameters(parameter)
    if owners is not None:
        names = [n for n in names if owners.get(n) == instrument]
        return {"qual": [n + "_qual" for n in names if n + "_qual" in qual], "unknown": []}
    return {"qual": [n + "_qual" for n in names if n + "_qual" in qual],
            "unknown": [n for n in names if n + "_qual" not in qual]}


def event_owners(instruments, log):
    """Assign each parameter name to the instrument whose events it belongs to, for routing the shared events file.
    instruments is {name: instance}. A name in an instrument's grid (the Level 2 variables) belongs to that
    instrument, otherwise a name in the variables of exactly one instrument belongs to it. Returns the owners
    {parameter: instrument} and the ambiguous names {parameter: [instruments]}."""
    owners = {}
    for name, instrument in instruments.items():
        for var in instrument.grid:
            if var in owners and owners[var] != name:
                log.warning("{} is a Level 2 variable of both {} and {}, shared events for it go to {}.".format(
                    var, owners[var], name, owners[var]), indent=1)
                continue
            owners[var] = name
    found = {}
    for name, instrument in instruments.items():
        for var in instrument.variables:
            if not var.endswith("_qual"):
                found.setdefault(var, []).append(name)
    ambiguous = {}
    for var, names in found.items():
        if var in owners:
            continue
        if len(names) == 1:
            owners[var] = names[0]
        else:
            ambiguous[var] = names
    return owners, ambiguous


def check_shared_events(events_file, owners, ambiguous, log):
    """Report once per run the parameters in the shared events file that cannot be routed to an instrument."""
    if not os.path.isfile(events_file):
        log.warning("Cannot find shared events file: {}.".format(events_file), indent=1)
        return
    events = parse_events(events_file, log)
    for event in events or []:
        if event["parameter"].strip().lower() == "all":
            continue
        for parameter in event_parameters(event["parameter"]):
            if parameter in owners:
                continue
            if parameter in ambiguous:
                log.warning("Parameter {} on line {} of {} is in several instruments ({}), put it in events_<instrument>.csv. Skipped.".format(
                    parameter, event["line"], events_file, ", ".join(ambiguous[parameter])), indent=1)
            else:
                log.warning("Unknown parameter {} on line {} of {}, skipped.".format(parameter, event["line"], events_file), indent=1)


def depth_tolerance(grid, depths):
    """Half the median bin spacing of the depth grid (or of the measured depths if there is no grid), plus 1e-6."""
    for values in (grid, depths):
        if values is None:
            continue
        values = np.unique(np.asarray(values, dtype=float)[np.isfinite(np.asarray(values, dtype=float))])
        if len(values) > 1:
            return float(np.median(np.diff(values))) / 2 + 1e-6
    return 1e-6


def parse_event_depths(spec, depths, log, line, tol):
    """Map an events depth spec (a value, a range "10-20" or a comma separated mix of both) to boolean masks over
    depths. Returns a list of (mask, low, high), one per item, or None if the spec cannot be parsed."""
    items = []
    for item in [i.strip() for i in spec.split(",") if i.strip()]:
        match = re.fullmatch(r"(-?\d+(?:\.\d*)?)\s*-\s*(-?\d+(?:\.\d*)?)", item)
        try:
            if match:
                low, high = float(match.group(1)), float(match.group(2))
                if low > high:
                    raise ValueError
                low, high = low - tol, high + tol
            else:
                value = float(item)
                low, high = value - tol, value + tol
        except ValueError:
            log.warning("Unable to parse depth '{}' in events line {}, event skipped.".format(spec, line), indent=4)
            return None
        mask = (depths >= low) & (depths <= high)
        if not mask.any():
            finite = depths[np.isfinite(depths)]
            available = "{:.2f} to {:.2f} m".format(finite.min(), finite.max()) if len(finite) else "none"
            log.warning("Depth {} in events line {} not present in the data (depths in event window: {}).".format(
                item, line, available), indent=4)
        items.append((mask, low, high))
    if not items:
        log.warning("Unable to parse depth '{}' in events line {}, event skipped.".format(spec, line), indent=4)
        return None
    return items


def json_converter(qa):
    for keys in qa.keys():
        try:
            if qa[keys]["simple"]["bounds"][0] == "-inf":
                qa[keys]["simple"]["bounds"][0] = -np.inf
            if qa[keys]["simple"]["bounds"][1] == "inf":
                qa[keys]["simple"]["bounds"][1] = np.inf
        except:
            pass
    try:
        if qa["time"]["simple"]["bounds"][1] == "now":
            qa["time"]["simple"]["bounds"][1] = datetime.now().timestamp()
        return qa
    except:
        return qa


def geographic_distance(latlng1, latlng2):
    lat1 = radians(latlng1[0])
    lon1 = radians(latlng1[1])
    lat2 = radians(latlng2[0])
    lon2 = radians(latlng2[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return 6373000.0 * c


def copy_variables(variables_dict):
    var_dict = dict()
    for var in variables_dict:
        var_dict[var] = variables_dict[var][:]
    nc_copy = copy.deepcopy(var_dict)
    return nc_copy


def position_in_array(arr, value):
    for i in range(len(arr)):
        if value < arr[i]:
            return i
    return len(arr)


def files_in_directory(root):
    f = []
    for path, subdirs, files in os.walk(root):
        for name in files:
            f.append(os.path.join(path, name))
    return f


def ctd_parse_metadata(file):
    metadata = {}
    with open(file, encoding="utf8", errors='ignore') as f:
        lines = f.readlines()
    parse = False
    for i in range(len(lines)):
        if "METADATA;" in lines[i]:
            parse = True
        elif "**********" in lines[i]:
            parse = False
        elif parse:
            d = str(lines[i]).replace(";", "").split(":")
            if "coordinates" in d[0].lower() and "grid" not in d[0].lower():
                c = d[1].strip().split("/")
                if float(c[0]) > 2000000:
                    metadata["latitude"], metadata["longitude"] = ch1903plus_to_latlng(float(c[0]), float(c[1]))
                elif float(c[0]) > 200:
                    metadata["latitude"], metadata["longitude"] = ch1903_to_latlng(float(c[0]), float(c[1]))
                else:
                    metadata["latitude"] = float(c[0])
                    metadata["longitude"] = float(c[0])
            metadata[d[0].replace("/", "")] = d[1].strip()
    return metadata


def latlng_to_ch1903(lat, lng):
    lat = lat * 3600
    lng = lng * 3600
    lat_aux = (lat - 169028.66) / 10000
    lng_aux = (lng - 26782.5) / 10000
    x = 2600072.37 + 211455.93 * lng_aux - 10938.51 * lng_aux * lat_aux - 0.36 * lng_aux * lat_aux ** 2 - 44.54 * lng_aux ** 3 - 2000000
    y = 1200147.07 + 308807.95 * lat_aux + 3745.25 * lng_aux ** 2 + 76.63 * lat_aux ** 2 - 194.56 * lng_aux ** 2 * lat_aux + 119.79 * lat_aux ** 3 - 1000000
    return x, y


def ch1903_to_latlng(x, y):
    x_aux = (x - 600000) / 1000000
    y_aux = (y - 200000) / 1000000
    lat = 16.9023892 + 3.238272 * y_aux - 0.270978 * x_aux ** 2 - 0.002528 * y_aux ** 2 - 0.0447 * x_aux ** 2 * y_aux - 0.014 * y_aux ** 3
    lng = 2.6779094 + 4.728982 * x_aux + 0.791484 * x_aux * y_aux + 0.1306 * x_aux * y_aux ** 2 - 0.0436 * x_aux ** 3
    lat = (lat * 100) / 36
    lng = (lng * 100) / 36
    return lat, lng


def latlng_to_ch1903plus(lat, lng):
    lat = lat * 3600
    lng = lng * 3600
    lat_aux = (lat - 169028.66) / 10000
    lng_aux = (lng - 26782.5) / 10000
    x = 2600072.37 + 211455.93 * lng_aux - 10938.51 * lng_aux * lat_aux - 0.36 * lng_aux * lat_aux ** 2 - 44.54 * lng_aux ** 3 - 2000000
    y = 1200147.07 + 308807.95 * lat_aux + 3745.25 * lng_aux ** 2 + 76.63 * lat_aux ** 2 - 194.56 * lng_aux ** 2 * lat_aux + 119.79 * lat_aux ** 3 - 1000000
    x = x + 2000000
    y = y + 1000000
    return x, y


def ch1903plus_to_latlng(x, y):
    x = x - 2000000
    y = y - 1000000
    x_aux = (x - 600000) / 1000000
    y_aux = (y - 200000) / 1000000
    lat = 16.9023892 + 3.238272 * y_aux - 0.270978 * x_aux ** 2 - 0.002528 * y_aux ** 2 - 0.0447 * x_aux ** 2 * y_aux - 0.014 * y_aux ** 3
    lng = 2.6779094 + 4.728982 * x_aux + 0.791484 * x_aux * y_aux + 0.1306 * x_aux * y_aux ** 2 - 0.0436 * x_aux ** 3
    lat = (lat * 100) / 36
    lng = (lng * 100) / 36
    return lat, lng


def first_centered_differences(x, y, fill=False):
    if x.size != y.size:
        raise ValueError("First-centered differences: vectors do not have the same size")
    dy = np.full(x.size, np.nan)
    iif = np.where((np.isfinite(x)) & (np.isfinite(y)))[0]
    if iif.size == 0:
        return dy
    x0 = x[iif]
    y0 = y[iif]
    dy0 = np.full(x0.size, np.nan)
    # calculates differences
    dy0[0] = (y0[1] - y0[0]) / (x0[1] - x0[0])
    dy0[-1] = (y0[-1] - y0[-2]) / (x0[-1] - x0[-2])
    dy0[1:-1] = (y0[2:] - y0[0:-2]) / (x0[2:] - x0[0:-2])

    dy[iif] = dy0

    if fill:
        dy[0:iif[0]] = dy[iif[0]]
        dy[iif[-1] + 1:] = dy[iif[-1]]
    return dy
