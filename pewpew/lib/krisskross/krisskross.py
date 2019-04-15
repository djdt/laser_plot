import numpy as np

from pewpew.lib.laser.laser import Laser
from pewpew.lib.krisskross.config import KrissKrossConfig
from pewpew.lib.krisskross.data import KrissKrossData

from typing import Dict, Tuple


# KKType = TypeVar("KKType", bound="KrissKross")  # For typing


class KrissKross(Laser):
    def __init__(
        self,
        data: Dict[str, KrissKrossData] = None,
        config: KrissKrossConfig = None,
        name: str = "",
        filepath: str = "",
    ):
        if config is None:
            config = KrissKrossConfig()

        super().__init__(  # type: ignore
            data=data, config=config, name=name, filepath=filepath
        )

    def get(
        self,
        name: str,
        calibrate: bool = False,
        extent: Tuple[float, float, float, float] = None,
        flat: bool = True,
        layer: int = None,
    ) -> np.ndarray:
        return self.data[name].get(  # type: ignore
            self.config, calibrate=calibrate, extent=extent, flat=flat, layer=layer
        )

    def get_structured(
        self,
        calibrate: bool = False,
        extent: Tuple[float, float, float, float] = None,
        flat: bool = True,
        layer: int = None,
    ) -> np.ndarray:
        data = []
        for isotope in self.isotopes():
            data.append(
                self.data[isotope].get(  # type: ignore
                    self.config,
                    calibrate=calibrate,
                    extent=extent,
                    flat=flat,
                    layer=layer,
                )
            )
        dtype = [(isotope, float) for isotope in self.isotopes()]
        structured = np.empty(data[0].shape, dtype)
        for isotope, d in zip(self.isotopes(), data):
            structured[isotope] = d
        return structured