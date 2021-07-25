import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets

from pewlib.laser import Laser
from pewlib.srr import SRRConfig

from pewpew.graphics import colortable
from pewpew.graphics.imageitems import (
    ScaledImageItem,
    RulerWidgetItem,
    ImageSliceWidgetItem,
)
from pewpew.graphics.selectionitems import (
    ScaledImageSelectionItem,
    LassoImageSelectionItem,
    RectImageSelectionItem,
)
from pewpew.graphics.options import GraphicsOptions
from pewpew.graphics.overlaygraphics import OverlayScene, OverlayView
from pewpew.graphics.overlayitems import (
    ColorBarOverlay,
    MetricScaleBarOverlay,
    LabelOverlay,
)

from pewpew.lib.numpyqt import array_to_image

from typing import Optional, List


class LaserGraphicsView(OverlayView):
    """The pewpew laser view.

    Displays the image with correct scaling and an overlay label, sizebar and colorbar.
    If a selection is made the 'mask' is updated and a highlight is applied to sselected pixels.
    """

    cursorValueChanged = QtCore.Signal(float, float, float)

    def __init__(self, options: GraphicsOptions, parent: QtWidgets.QWidget = None):
        self.options = options
        self.data: Optional[np.ndarray] = None
        self.mask: Optional[np.ndarray] = None

        self._scene = OverlayScene(0, 0, 640, 480)
        self._scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))

        super().__init__(self._scene, parent)
        self.cursors["selection"] = QtCore.Qt.ArrowCursor

        self.image: Optional[ScaledImageItem] = None
        self.selection_item: Optional[ScaledImageSelectionItem] = None
        self.selection_image: Optional[ScaledImageItem] = None
        self.widget: Optional[QtWidgets.QGraphicsItem] = None

        self.label = LabelOverlay(
            "_", font=self.options.font, color=self.options.font_color
        )
        self.scalebar = MetricScaleBarOverlay(
            font=self.options.font, color=self.options.font_color
        )
        self.colorbar = ColorBarOverlay(
            [], 0, 1, font=self.options.font, color=self.options.font_color
        )

        self.scene().addOverlayItem(
            self.label,
            QtCore.Qt.TopLeftCorner,
            QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft,
        )
        self.label.setPos(10, 10)
        self.scene().addOverlayItem(
            self.scalebar,
            QtCore.Qt.TopRightCorner,
            QtCore.Qt.AlignTop | QtCore.Qt.AlignRight,
        )
        self.scalebar.setPos(0, 10)
        self.scene().addOverlayItem(
            self.colorbar,
            QtCore.Qt.BottomLeftCorner,
            QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft,
        )

    def mapToData(self, pos: QtCore.QPointF) -> QtCore.QPoint:
        """Maps point to image pixel."""
        if self.image is None:
            return QtCore.QPoint(0, 0)

        return self.image.mapToData(pos)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        pos = self.mapToScene(event.pos())
        if (
            self.image is not None
            and self.image.rect.left() < pos.x() < self.image.rect.right()
            and self.image.rect.top() < pos.y() < self.image.rect.bottom()
        ):
            dpos = self.mapToData(pos)
            self.cursorValueChanged.emit(
                pos.x(), pos.y(), self.data[dpos.y(), dpos.x()]
            )
        else:
            self.cursorValueChanged.emit(pos.x(), pos.y(), np.nan)

    def startLassoSelection(self) -> None:
        """Select image pixels using a lasso."""
        if self.image is None:
            return
        if self.selection_item is not None:
            self.scene().removeItem(self.selection_item)

        self.selection_item = LassoImageSelectionItem(self.image)
        self.selection_item.selectionChanged.connect(self.drawSelectionImage)
        self.scene().addItem(self.selection_item)
        self.selection_item.grabMouse()
        self.setInteractionFlag("selection")

    def startRectangleSelection(self) -> None:
        """Select image pixels using a rectangle."""
        if self.image is None:
            return
        if self.selection_item is not None:
            self.scene().removeItem(self.selection_item)

        self.selection_item = RectImageSelectionItem(self.image)
        self.selection_item.selectionChanged.connect(self.drawSelectionImage)
        self.scene().addItem(self.selection_item)
        self.selection_item.grabMouse()
        self.setInteractionFlag("selection")

    def endSelection(self) -> None:
        """End selection and remove highlight."""
        if self.selection_item is not None:
            self.selection_item = None
            self.scene().removeItem(self.selection_item)
        if self.selection_image is not None:
            self.scene().removeItem(self.selection_image)
            self.selection_image = None

        self.mask = np.zeros(self.data.shape, dtype=bool)
        self.setInteractionFlag("selection", False)

    def posInSelection(self, pos: QtCore.QPointF) -> bool:
        """Is the pos in the selected area."""
        if self.mask is None:
            return False
        pos = self.mapToData(self.mapToScene(pos))
        return self.mask[pos.y(), pos.x()]

    def startRulerWidget(self) -> None:
        """Measure distances using a ruler."""
        if self.image is None:
            return
        if self.widget is not None:
            self.scene().removeItem(self.widget)
        self.widget = RulerWidgetItem(self.image, font=self.options.font)
        self.widget.setZValue(1)
        self.scene().addItem(self.widget)
        self.widget.grabMouse()
        self.setInteractionFlag("widget")

    def startSliceWidget(self) -> None:
        """Display 1d slices in image."""
        if self.image is None or self.data is None:
            return
        if self.widget is not None:
            self.scene().removeItem(self.widget)
        self.widget = ImageSliceWidgetItem(
            self.image, self.data, font=self.options.font
        )
        self.widget.setZValue(1)
        self.scene().addItem(self.widget)
        self.widget.grabMouse()
        self.setInteractionFlag("widget")

    def endWidget(self) -> None:
        """End and remove any widgets."""
        if self.widget is not None:
            self.scene().removeItem(self.widget)
        self.widget = None
        self.setInteractionFlag("widget", False)

    def drawImage(self, data: np.ndarray, rect: QtCore.QRectF, name: str) -> None:
        """Draw 'data' into 'rect'.

        Args:
            data: image data
            rect: image extent
            name: label of data
        """
        if self.image is not None:
            self.scene().removeItem(self.image)

        self.data = np.ascontiguousarray(data)

        vmin, vmax = self.options.get_colorrange_as_float(name, self.data)
        table = colortable.get_table(self.options.colortable)

        data = np.clip(self.data, vmin, vmax)
        if vmin != vmax:  # Avoid div 0
            data = (data - vmin) / (vmax - vmin)

        image = array_to_image(data)
        image.setColorTable(table)
        self.image = ScaledImageItem(image, rect, smooth=self.options.smoothing)
        self.scene().addItem(self.image)

        self.colorbar.updateTable(table, vmin, vmax)

        if self.sceneRect() != rect:
            self.setSceneRect(rect)
            self.fitInView(rect, QtCore.Qt.KeepAspectRatio)

    def drawSelectionImage(self, mask: np.ndarray, modes: List[str]) -> None:
        """Highlight selected regions.

        The mask can be added to, subtracted, intersected or differentiated from
        the current selection using 'modes'.

        Args:
            mask: bool array of pixels to highlight
            modes: operation, ['add', 'subtract', 'intersect', 'difference']
        """
        if self.selection_image is not None:
            self.scene().removeItem(self.selection_image)

        if self.mask is None:
            self.mask = np.zeros(self.data.shape, dtype=bool)

        mask = mask.astype(bool)
        if "add" in modes:
            self.mask = np.logical_or(self.mask, mask)
        elif "subtract" in modes:
            self.mask = np.logical_and(self.mask, ~mask)
        elif "intersect" in modes:
            self.mask = np.logical_and(self.mask, mask)
        elif "difference" in modes:
            self.mask = np.logical_xor(self.mask, mask)
        else:
            self.mask = mask

        color = QtGui.QColor(255, 255, 255, a=128)

        self.selection_image = ScaledImageItem.fromArray(
            self.mask.astype(np.uint8),
            self.image.rect,
            colortable=[0, int(color.rgba())],
        )
        self.selection_image.setZValue(self.image.zValue() + 1.0)
        self.scene().addItem(self.selection_image)

    def drawLaser(self, laser: Laser, name: str, layer: int = None) -> None:
        """Draw image of laser.

        Args:
            laser: laser object
            name: name of element to draw
            layer: layer to draw (SRRLaser only)
        """
        kwargs = {"calibrate": self.options.calibrate, "layer": layer, "flat": True}

        data = laser.get(name, **kwargs)
        unit = laser.calibration[name].unit if self.options.calibrate else ""

        # Get extent
        if isinstance(laser.config, SRRConfig):
            x0, x1, y0, y1 = laser.config.data_extent(data.shape, layer=layer)
        else:
            x0, x1, y0, y1 = laser.config.data_extent(data.shape)
        rect = QtCore.QRectF(x0, y0, x1 - x0, y1 - y0)
        # Recoordinate the top left to 0,0 for correct updating
        rect.moveTopLeft(QtCore.QPointF(0.0, 0.0))

        # Update overlay items
        self.label.setText(name)
        self.colorbar.unit = unit

        # Set overlay items visibility
        self.setOverlayItemVisibility()

        self.drawImage(data, rect, name)
        self.updateForeground()

    def setOverlayItemVisibility(
        self, label: bool = None, scalebar: bool = None, colorbar: bool = None
    ):
        """Set visibility of overlay items."""
        if label is None:
            label = self.options.items["label"]
        if scalebar is None:
            scalebar = self.options.items["scalebar"]
        if colorbar is None:
            colorbar = self.options.items["colorbar"]

        self.label.setVisible(label)
        self.scalebar.setVisible(scalebar)
        self.colorbar.setVisible(colorbar)

    def zoomStart(self) -> None:
        """Start zoom interactions."""
        self.setInteractionFlag("zoom", True)
