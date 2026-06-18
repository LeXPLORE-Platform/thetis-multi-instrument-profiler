# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import argparse
from instruments import CTD, DO, PAR, TRIP1, TRIP2, ACS, OCR1, OCR2, process_grid
from general.functions import logger, files_in_directory
from functions import retrieve_new_files, parse_ids_from_files

def main(server=False, logs=False):
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if logs:
        log = logger(os.path.join(repo, "logs/thetis"))
    else:
        log = logger()
    log.initialise("Processing Lexplore Thetis data")
    directories = {f: os.path.join(repo, "data", f) for f in ["Level0", "Level1", "Level2"]}
    for directory in directories:
        os.makedirs(directories[directory], exist_ok=True)
    directories["Level0"] = os.path.join(directories["Level0"], "Processed")
    calibration = os.path.join(repo, "calibration")
    edited_files = []

    log.begin_stage("Collecting inputs")
    if server:
        log.info("Processing files from sftp server")
        if not os.path.exists(os.path.join(repo, "creds.json")):
            raise ValueError("Credential file required to retrieve live data from the fstp server.")
        with open(os.path.join(repo, "creds.json"), 'r') as f:
            creds = json.load(f)
        files = retrieve_new_files(directories["Level0"], creds, server_location="data/Thetis", filetype=".txt")
        edited_files = edited_files + files
    else:
        files = files_in_directory(directories["Level0"])
        files.sort()
        log.info("Reprocessing complete dataset from {}".format(directories["Level0"]))
    log.end_stage()

    log.begin_stage("Processing data...")
    ids = parse_ids_from_files(files)

    for id in ids:
        l2_datasets = {}
        sensor = CTD()
        id_code = id.split("/")[-1]
        if sensor.read_data(id, directories["Level0"]):
            sensor.multiple_profiles()
            sensor.quality_assurance(file_path="notes/quality_assurance.json")
            edited_files.extend(sensor.export(os.path.join(directories["Level1"], "CTD"), "L1_LexploreThetis_CTD_" + id_code))
            sensor.mask_data()
            ctd_data = sensor.export_data()
            l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "depth")

            sensor = DO()
            if sensor.read_data(id, directories["Level0"], ctd_data):
                sensor.multiple_profiles()
                sensor.quality_assurance(file_path="notes/quality_assurance.json")
                edited_files.extend(sensor.export(os.path.join(directories["Level1"], "DO"), "L1_LexploreThetis_DO" + id_code))
                sensor.mask_data()
                l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "depth")

            sensor = PAR()
            if sensor.read_data(id, directories["Level0"], ctd_data):
                sensor.multiple_profiles()
                sensor.quality_assurance(file_path="notes/quality_assurance.json")
                edited_files.extend(sensor.export(os.path.join(directories["Level1"], "PAR"), "L1_LexploreThetis_PAR" + id_code))
                sensor.mask_data()
                l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "depth")

            sensor = TRIP1()
            if sensor.read_data(id, directories["Level0"], ctd_data):
                sensor.multiple_profiles()
                sensor.quality_assurance(file_path="notes/quality_assurance.json")
                edited_files.extend(sensor.export(os.path.join(directories["Level1"], "TRIP1"), "L1_LexploreThetis_TRIP1" + id_code))
                sensor.mask_data()
                l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "depth")

            sensor = TRIP2()
            if sensor.read_data(id, directories["Level0"], ctd_data):
                sensor.multiple_profiles()
                sensor.quality_assurance(file_path="notes/quality_assurance.json")
                edited_files.extend(sensor.export(os.path.join(directories["Level1"], "TRIP2"), "L1_LexploreThetis_TRIP2" + id_code))
                sensor.mask_data()
                l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "depth")

            sensor = ACS()
            if sensor.read_data(id, directories["Level0"], calibration, ctd_data):
                sensor.quality_assurance(file_path="notes/quality_assurance.json")
                sensor.custom_quality_flags()
                edited_files.extend(sensor.export(os.path.join(directories["Level1"], "ACS"), "L1_LexploreThetis_ACS" + id_code))
                sensor.mask_data()
                l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "depth")

            sensor = OCR1()
            if sensor.read_data(id, directories["Level0"], calibration, ctd_data):
                sensor.quality_assurance(file_path="notes/quality_assurance.json")
                edited_files.extend(sensor.export(os.path.join(directories["Level1"], "OCR1"), "L1_LexploreThetis_OCR1" + id_code))
                sensor.mask_data()
                l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "wavelength")

            sensor = OCR2()
            if sensor.read_data(id, directories["Level0"], calibration, ctd_data):
                sensor.quality_assurance(file_path="notes/quality_assurance.json")
                edited_files.extend(sensor.export(os.path.join(directories["Level1"], "OCR2"), "L1_LexploreThetis_OCR2" + id_code))
                sensor.mask_data()
                l2_datasets = sensor.resample_to_fixed_grid(l2_datasets, "wavelength")

            grid = process_grid()
            l2_datasets = grid.radiance_products(l2_datasets)
            grid.createl2product(directories["Level2"], l2_datasets)
    log.end_stage()

    return edited_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', '-s', help="Collect and process new files from FTP server", action='store_true')
    parser.add_argument('--logs', '-l', help="Write logs to file", action='store_true')
    args = vars(parser.parse_args())
    main(server=args["server"], logs=args["logs"])
