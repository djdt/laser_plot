import numpy as np
from pewlib.laser import Laser
from PySide6 import QtCore, QtGui

from pewpew.graphics import colortable
from pewpew.graphics.options import GraphicsOptions
from pewpew.graphics.overlayitems import MetricScaleBarOverlay
from pewpew.graphics.util import path_for_colorbar_labels
from pewpew.lib.numpyqt import array_to_image


def position_for_alignment(
    bounds: QtCore.QRectF, rect: QtCore.QRectF, alignment: QtCore.Qt.AlignmentFlag
) -> QtCore.QPointF:
    rect.moveTopLeft(bounds.topLeft())
    if alignment & QtCore.Qt.AlignRight:
        rect.moveRight(bounds.right())
    elif alignment & QtCore.Qt.AlignHCenter:
        rect.moveCenter(QtCore.QPointF(bounds.center().x(), rect.center().y()))
    if alignment & QtCore.Qt.AlignBottom:
        rect.moveBottom(bounds.bottom())
    elif alignment & QtCore.Qt.AlignVCenter:
        rect.moveCenter(QtCore.QPointF(rect.center().x(), bounds.center().y()))
    return rect


def generate_laser_image(
    laser: Laser,
    element: str,
    options: GraphicsOptions,
    scalebar_alignment: QtCore.Qt.AlignmentFlag
    | None = QtCore.Qt.AlignmentFlag.AlignTop
    | QtCore.Qt.AlignmentFlag.AlignRight,
    label_alignment: QtCore.Qt.AlignmentFlag
    | None = QtCore.Qt.AlignmentFlag.AlignTop
    | QtCore.Qt.AlignmentFlag.AlignLeft,
    colorbar: bool = True,
    raw: bool = False,
) -> QtGui.QImage:
    data = laser.get(element, calibrate=options.calibrate, flat=True)
    data = np.ascontiguousarray(data)

    vmin, vmax = options.get_color_range_as_float(element, data)
    table = colortable.get_table(options.colortable)

    data = np.clip(data, vmin, vmax)
    if vmin != vmax:  # Avoid div 0
        data = (data - vmin) / (vmax - vmin)

    image = array_to_image(data)
    image.setColorTable(table)
    image.setColorCount(len(table))

    if raw:
        return laser

    fm = QtGui.QFontMetrics(options.font)
    xh = fm.xHeight()
    image = image.scaled(image.size() * 2.0)
    size = image.size()

    if colorbar:  # make room for colorbar
        size = size.grownBy(QtCore.QMargins(0, 0, 0, xh + xh / 2.0 + fm.height()))
    colorbar_unit = (
        colorbar and options.calibrate and laser.calibration[element].unit is not None
    )
    if colorbar_unit:
        size = size.grownBy(QtCore.QMargins(0, 0, 0, fm.height()))

    pixmap = QtGui.QPixmap(size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)

    pen = QtGui.QPen(QtCore.Qt.black, 2.0)
    pen.setCosmetic(True)

    painter = QtGui.QPainter(pixmap)
    painter.setFont(options.font)
    # Draw the image
    painter.drawImage(image.rect(), image, image.rect())

    if colorbar:
        rect = QtCore.QRectF(
            image.rect().left(), image.rect().bottom() + xh / 2.0, image.width(), xh
        )
        _data = np.arange(256, dtype=np.uint8)
        cbar = QtGui.QImage(_data, 256, 1, 256, QtGui.QImage.Format_Indexed8)
        cbar.setColorTable(table)
        cbar.setColorCount(len(table))

        painter.drawImage(rect, cbar)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        path = path_for_colorbar_labels(options.font, vmin, vmax, rect.width())
        if colorbar_unit:
            text = laser.calibration[element].unit
            path.addText(
                rect.width()
                - fm.boundingRect(text).width()
                - fm.lineWidth()
                - fm.rightBearing(text[-1]),
                fm.ascent() + fm.height(),
                painter.font(),
                text,
            )
        path.translate(rect.bottomLeft())
        painter.strokePath(path, pen)
        painter.fillPath(path, QtGui.QBrush(QtCore.Qt.GlobalColor.white))

    painter.setRenderHint(QtGui.QPainter.Antialiasing)

    # Draw the element label
    if label_alignment is not None:
        rect = painter.boundingRect(
            image.rect().adjusted(xh, xh, -xh, -xh), label_alignment, element
        )
        path = QtGui.QPainterPath()
        path.addText(rect.left(), rect.top() + fm.ascent(), painter.font(), element)
        painter.strokePath(path, pen)
        painter.fillPath(path, QtGui.QBrush(QtCore.Qt.GlobalColor.white))

    # Draw the scale-bar
    if scalebar_alignment is not None:
        rect = QtCore.QRectF(0, 0, xh * 10.0, fm.height())
        rect = position_for_alignment(
            image.rect().adjusted(xh, xh, -xh, -xh), rect, scalebar_alignment
        )

        x0, x1, y0, y1 = laser.extent
        scale = (x1 - x0) / image.rect().width()

        width, unit = MetricScaleBarOverlay.getWidthAndUnit(rect.width() * scale, "μm")
        text = f"{width * 1e-6 / MetricScaleBarOverlay.units[unit]:.3g} {unit}"
        width = width / scale

        path = QtGui.QPainterPath()
        path.addText(
            rect.center().x() - fm.boundingRect(text).width() / 2.0,
            rect.top() + fm.ascent(),
            painter.font(),
            text,
        )

        painter.strokePath(path, pen)
        painter.fillPath(path, QtGui.QBrush(QtCore.Qt.GlobalColor.white))

        # Draw the bar
        bar = QtCore.QRectF(
            rect.center().x() - width / 2.0, rect.top() + fm.height(), width, xh / 2.0
        )
        painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.white))
        painter.drawRect(bar)

    painter.end()
    return pixmap.toImage()
