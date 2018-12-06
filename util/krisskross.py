import numpy as np

from util.laser import LaserData


def krissKrossLayers(layers, aspect, warmup, horizontal_first=True):

    j = 0 if horizontal_first else 1
    aspect = int(aspect)
    trim = int(aspect / 2)
    # Calculate the line lengths
    length = (layers[1].shape[0] * aspect, layers[0].shape[0] * aspect)

    # Reshape the layers and stack into matrix
    transformed = []
    for i, layer in enumerate(layers):
        # Trim data of warmup time and excess
        layer = layer[:, warmup:warmup + length[(i + j) % 2]]
        # Stretch array
        layer = np.repeat(layer, aspect, axis=0)
        # Flip vertical layers and trim
        if (i + j) % 2 == 1:
            layer = layer.T
            layer = layer[trim:, trim:]
        elif trim > 0:
            layer = layer[:-trim, :-trim]

        transformed.append(layer)

    data = np.dstack(transformed)

    return data


class KrissKrossData(LaserData):
    def __init__(self, data=None, config=None, calibration=None, source=""):
        super().__init__(
            data=data, config=config, calibration=calibration, source=source)

    def fromLayers(self, layers, warmup_time=13.0, horizontal_first=True):
        warmup = int(warmup_time / self.config['scantime'])
        self.data = krissKrossLayers(layers, self.aspect(), warmup,
                                     horizontal_first)

    def get(self,
            isotope=None,
            calibrated=False,
            trimmed=False,
            flattened=True):
        data = super().get(
            isotope=isotope, calibrated=calibrated, trimmed=trimmed)
        if flattened:
            data = np.mean(data, axis=2)
        return data

    def split(self):
        lds = []
        for data in np.dsplit(self.data, self.data.shape[2]):
            # Strip the third dimension
            lds.append(
                KrissKrossData(
                    data=data,
                    config=self.config,
                    calibration=self.calibration,
                    source=self.source))
        return lds

    def extent(self, trimmed=False):
        # Image data is stored [rows][cols]
        extent = super().extent(trimmed)
        extent[3] /= self.aspect()
        return extent

    def layers(self):
        return self.data.shape[2]
