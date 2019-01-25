import numpy as np
import os

from pewpew import __version__
from pewpew.lib.exceptions import PewPewConfigError, PewPewDataError, PewPewFileError
from pewpew.lib.formatter import formatIsotope
from pewpew.lib.laser import LaserData


def load(
    path: str,
    isotope: str = "Unknown",
    config: dict = None,
    calibration: dict = None,
    read_config: bool = True,
) -> LaserData:
    """Imports the given CSV file, returning a LaserData object.

    Each row of the CSV is read as a line of laser data.
    An optional # commented header (see exportCsv) containing
    configuration data may also be read.

    Args:
        path: Path to the CSV file
        isotope: Name of the isotope
        config: Laser configuration to apply
        calibration: Calibration to apply
        read_config: If True, attempts to read config from header data

    Returns:
        The LaserData object.

    Raises:
        PewPewFileError: Malformed file.
        PewPewConfigError: Invalid config.
        PewPewDataError: Invalild data.

    """
    with open(path, "r") as fp:
        line = fp.readline().strip()
        if line == "# Pew Pew Export":  # CSV generated by pewpew
            isotope = fp.readline().strip().lstrip("# ")
            # Read the config from the file
            if read_config:
                if config is None:
                    config = dict(LaserData.DEFAULT_CONFIG)
                line = fp.readline().strip().lstrip("# ")
                if ";" not in line or "=" not in line:
                    raise PewPewFileError(f"Malformed config line '{line}'.")

                for token in line.split(";"):
                    k, v = token.split("=")
                    if k not in config.keys():
                        raise PewPewConfigError(f"Invalid config key '{k}'.")
                    try:
                        config[k] = float(v)
                    except ValueError as e:
                        raise PewPewConfigError(f"Invalid value '{v}'.") from e

        try:
            data = np.genfromtxt(fp, delimiter=",", dtype=np.float64, comments="#")
        except ValueError as e:
            raise PewPewFileError("Could not parse file.") from e

    if data.ndim != 2:
        raise PewPewDataError(f"Invalid data dimensions '{data.ndim}'.")

    isotope = formatIsotope(isotope)

    structured = np.empty(data.shape, dtype=[(isotope, np.float64)])
    structured[isotope] = data
    return LaserData(
        data=structured,
        config=config,
        calibration=calibration,
        name=os.path.splitext(os.path.basename(path))[0],
        source=path,
    )


def save(
    path: str,
    laser: LaserData,
    isotope: str,
    trimmed: bool = False,
    include_header: bool = False,
):
    header = None
    if include_header:
        config = laser.config
        calibration = laser.calibration
        header = (
            f"Pew Pew {__version__}\nisotope={isotope}\n"
            f"spotsize={config['spotsize']};speed={config['speed']};"
            f"scantime={config['scantime']}\n"
            f"intercept={calibration[isotope]['intercept']};"
            f"gradient={calibration[isotope]['gradient']};"
            f"unit={calibration[isotope]['unit']}\n"
        )
    np.savetxt(
        path,
        laser.get(isotope, calibrated=True, trimmed=trimmed),
        delimiter=",",
        header=header,
    )
