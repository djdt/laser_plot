import numpy as np
import os

from util.laser import LaserData


def importCsv(path, config_override=None, calibration=None):
    with open(path, "r") as fp:
        line = fp.readline().strip()
        isotope = fp.readline().strip().lstrip("#")
        line = fp.readline().strip()
        if config_override is None:
            config = LaserData.DEFAULT_CONFIG
            tokens = line.split(";")
            for token in tokens:
                k, v = token.split("=")
                config[k] = float(v)
        else:
            config = config_override
        # Remove any trim
        config["trim"] = [0, 0]

        data = np.genfromtxt(fp, delimiter=",", dtype=np.float64)

    structured = np.empty(data.shape, dtype=[(isotope, np.float64)])
    structured[k] = data
    return LaserData(
        data=structured,
        config=config,
        calibration=calibration,
        name=os.path.splitext(os.path.basename(path))[1],
        source=path,
    )


def importNpz(path, config_override=None, calibration_override=None):
    """Imports the numpy archive given. Both the config and calibration are
    read from the archive but can be overriden.

    path -> path to numpy archive
    config_override -> if not None will be applied to all imports
    calibration -> if not None will be applied to all imports

    returns list of LaserData/KrissKrossData"""
    lds = []
    npz = np.load(path)

    for i, (type, config, calibration) in enumerate(
        zip(npz["_type"], npz["_config"], npz["_calibration"])
    ):
        lds.append(
            type(
                data=npz[f"_data{i}"],
                config=config_override if config_override is not None else config,
                calibration=calibration_override
                if calibration_override is not None
                else calibration,
                name=os.path.splitext(os.path.basename(path))[1],
                source=path,
            )
        )
    return lds


def importAgilentBatch(path, config, calibration=None):
    """Scans the given path for .d directories containg a  similarly named
       .csv file. These are imported as lines and sorted by their name.

       path -> path to the .b directory
       config -> config to be applied
       calibration -> calibration to be applied

       returns LaserData"""
    data_files = []
    with os.scandir(path) as it:
        for entry in it:
            if entry.name.lower().endswith(".d") and entry.is_dir():
                file_name = entry.name[: entry.name.rfind(".")] + ".csv"
                data_files.append(os.path.join(entry.path, file_name))
    # Sort by name
    data_files.sort()

    with open(data_files[0], "r") as fp:
        line = fp.readline()
        skip_header = 0
        while line and not line.startswith("Time [Sec]"):
            line = fp.readline()
            skip_header += 1

        skip_footer = 0
        if "Print" in fp.read().splitlines()[-1]:
            skip_footer = 1

    cols = np.arange(1, line.count(",") + 1)

    lines = [
        np.genfromtxt(
            f,
            delimiter=",",
            names=True,
            usecols=cols,
            skip_header=skip_header,
            skip_footer=skip_footer,
            dtype=np.float64,
        )
        for f in data_files
    ]
    data = np.vstack(lines)

    return LaserData(
        data,
        config=config,
        calibration=calibration,
        name=os.path.splitext(os.path.basename(path))[1],
        source=path,
    )


def importThermoiCapLaser(path, config, calibration=None):
    """Imports data exported using \"Laser Data Reduction\".
    CSVs in the given directory are imported as
    lines in the image and are sorted by name.

    path -> path to directory containing CSVs
    config -> config to apply
    calibration -> calibration to apply

    returns LaserData"""
    data_files = []
    with os.scandir(path) as it:
        for entry in it:
            if entry.name.lower().endswith(".csv") and entry.is_file():
                data_files.append(entry.path)
    # Sort by name
    data_files.sort()

    with open(data_files[0], "r") as fp:
        line = fp.readline()
        skip_header = 0
        while line and not line.startswith("Time"):
            line = fp.readline()
            skip_header += 1

        delimiter = line[-1]

    cols = np.arange(1, line.count(delimiter))

    lines = [
        np.genfromtxt(
            f,
            delimiter=delimiter,
            names=True,
            usecols=cols,
            skip_header=skip_header,
            dtype=np.float64,
        )
        for f in data_files
    ]
    # We need to skip the first row as it contains junk
    data = np.vstack(lines)[1:]

    return LaserData(data, config=config, calibration=calibration, source=path)


def importThermoiCapCSV(path, config, calibration=None):
    """Imports data exported using the CSV export function.
    Exports must include the \"Counts\" column.

    path -> path to CSV
    config -> config to apply
    calibration -> calibration to apply

    returns LaserData"""
    data = {}
    with open(path, "r") as fp:
        # Find delimiter
        line = fp.readline().strip()
        delimiter = line[-1]
        # Skip row
        line = fp.readline()
        # First real row
        line = fp.readline()
        while line:
            _, _, isotope, data_type, line_data = line.split(delimiter, 4)
            if data_type == "Counter":
                data.setdefault(isotope, []).append(
                    np.genfromtxt(
                        [line_data],
                        delimiter=delimiter,
                        dtype=np.float64,
                        filling_values=0.0,
                    )
                )
            line = fp.readline()

    # Read the keys to ensure order is same
    keys = list(data.keys())
    # Stack lines to form 2d
    for k in keys:
        # Last line is junk
        data[k] = np.vstack(data[k])[:, :-1].transpose()
    # Build a named array out of data
    dtype = [(k, np.float64) for k in keys]
    structured = np.empty(data[keys[0]].shape, dtype)
    for k in keys:
        structured[k] = data[k]
    return LaserData(
        structured,
        config=config,
        calibration=calibration,
        name=os.path.splitext(os.path.basename(path))[1],
        source=path,
    )
