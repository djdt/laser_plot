import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets

from pewpew.graphics.imageitems import SnapImageItem
from pewpew.graphics.selectionitems import (
    LassoImageSelectionItem,
    RectImageSelectionItem,
    SnapImageSelectionItem,
)
from pewpew.graphics.widgetitems import (
    ImageSliceWidgetItem,
    RulerWidgetItem,
    WidgetItem,
)
from pewpew.graphics.options import GraphicsOptions
from pewpew.graphics.overlaygraphics import OverlayScene, OverlayView
from pewpew.graphics.overlayitems import (
    ColorBarOverlay,
    MetricScaleBarOverlay,
)

from typing import Optional


class LaserGraphicsView(OverlayView):
    """The pewpew laser view.

    Displays the image with correct scaling and an overlay label, sizebar and colorbar.
    If a selection is made the 'mask' is updated and a highlight is applied to sselected pixels.
    """

    cursorValueChanged = QtCore.Signal(float, float, float)

    def __init__(
        self, options: GraphicsOptions, parent: Optional[QtWidgets.QWidget] = None
    ):
        self.options = options
        self.data: Optional[np.ndarray] = None
        self.mask: Optional[np.ndarray] = None

        self._scene = OverlayScene(0, 0, 640, 480)
        self._scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))

        super().__init__(self._scene, parent)
        self.cursors["selection"] = QtCore.Qt.ArrowCursor

        # self.label = LabelOverlay(
        #     "_", font=self.options.font, color=self.options.font_color
        # )
        self.scalebar = MetricScaleBarOverlay(
            font=self.options.font, color=self.options.font_color
        )
        self.colorbar = ColorBarOverlay(
            [], 0, 1, font=self.options.font, color=self.options.font_color
        )

        # self.scene().addOverlayItem(
        #     self.label,
        #     QtCore.Qt.TopLeftCorner,
        #     QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft,
        # )
        # self.label.setPos(10, 10)
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

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        items = [
            item for item in self.items(event.pos()) if isinstance(item, SnapImageItem)
        ]
        pos = self.mapToScene(event.pos())

        if len(items) > 0:
            item = items[0]  # Todo, test Z-values
            self.cursorValueChanged.emit(pos.x(), pos.y(), item.dataAtPos(pos))
        else:
            self.cursorValueChanged.emit(pos.x(), pos.y(), np.nan)

    def startLassoSelection(self) -> None:
        """Select image pixels using a lasso."""
        for item in self.items():
            if isinstance(item, SnapImageSelectionItem):
                self.scene().removeItem(item)

        selection_item = LassoImageSelectionItem(parent=None)
        self.scene().addItem(selection_item)
        selection_item.grabMouse()
        self.setInteractionFlag("selection")

    def startRectangleSelection(self) -> None:
        """Select image pixels using a rectangle."""
        for item in self.items():
            if isinstance(item, SnapImageSelectionItem):
                self.scene().removeItem(item)

        selection_item = RectImageSelectionItem(parent=None)
        self.scene().addItem(selection_item)
        selection_item.grabMouse()
        self.setInteractionFlag("selection")

    def endSelection(self) -> None:
        """End selection and remove highlight."""
        for item in self.items():
            if isinstance(item, SnapImageSelectionItem):
                self.scene().removeItem(item)
            elif isinstance(item, SnapImageItem):
                item.handleSelection(np.zeros([], dtype=bool), [])

        self.setInteractionFlag("selection", False)

    def startRulerWidget(self) -> None:
        """Measure distances using a ruler."""
        for item in self.items():
            if isinstance(item, RulerWidgetItem):
                self.scene().removeItem(item)

        widget = RulerWidgetItem(font=self.options.font)
        widget.setZValue(10)
        self.scene().addItem(widget)
        widget.grabMouse()
        self.setInteractionFlag("widget")

    def startSliceWidget(self) -> None:
        """Display 1d slices in image."""
        for item in self.items():
            if isinstance(item, ImageSliceWidgetItem):
                self.scene().removeItem(item)

        widget = ImageSliceWidgetItem(font=self.options.font)
        widget.setZValue(10)
        self.scene().addItem(widget)
        widget.grabMouse()
        self.setInteractionFlag("widget")

    def endWidget(self) -> None:
        """End and remove any widgets."""
        for item in self.items():
            if isinstance(item, WidgetItem):
                self.scene().removeItem(item)
        self.setInteractionFlag("widget", False)

    def setOverlayItemVisibility(
        self,
        label: Optional[bool] = None,
        scalebar: Optional[bool] = None,
        colorbar: Optional[bool] = None,
    ):
        """Set visibility of overlay items."""
        # if label is None:
        #     label = self.options.overlay_items["label"]
        if scalebar is None:
            scalebar = self.options.overlay_items["scalebar"]
        if colorbar is None:
            colorbar = self.options.overlay_items["colorbar"]

        # self.label.setVisible(label)
        self.scalebar.setVisible(scalebar)
        self.colorbar.setVisible(colorbar)

    def zoomReset(self) -> None:
        rect = QtCore.QRectF(0, 0, 0, 0)
        for item in self.scene().items():
            if isinstance(item, SnapImageItem):
                rect = rect.united(item.boundingRect())
        self.scene().setSceneRect(rect)
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)

    def zoomStart(self) -> None:
        """Start zoom interactions."""
        self.setInteractionFlag("zoom", True)
