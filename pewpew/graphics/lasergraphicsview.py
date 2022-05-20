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
from pewpew.graphics.overlaygraphics import OverlayGraphicsView
from pewpew.graphics.overlayitems import (
    ColorBarOverlay,
    MetricScaleBarOverlay,
)

from typing import Optional


class LaserGraphicsView(OverlayGraphicsView):
    """The pewpew laser view.

    Displays the image with correct scaling and an overlay label, sizebar and colorbar.
    If a selection is made the 'mask' is updated and a highlight is applied to sselected pixels.
    """

    def __init__(
        self, options: GraphicsOptions, parent: Optional[QtWidgets.QWidget] = None
    ):
        super().__init__(QtWidgets.QGraphicsScene(QtCore.QRectF(0, 0, 1, 1), parent), parent)

        self.options = options
        self.cursors["selection"] = QtCore.Qt.ArrowCursor

        self.scalebar = MetricScaleBarOverlay(
            font=self.options.font, color=self.options.font_color
        )
        self.colorbar = ColorBarOverlay(
            [], 0, 1, font=self.options.font, color=self.options.font_color
        )

        self.addOverlayItem(self.scalebar)
        self.scalebar.setPos(0, 10)
        self.addOverlayItem(self.colorbar)

        self.viewScaleChanged.connect(self.scalebar.requestPaint)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self.clearFocus()
        event.accept()

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
                item.select(np.zeros([], dtype=bool), [])

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
        scalebar: Optional[bool] = None,
        colorbar: Optional[bool] = None,
    ):
        """Set visibility of overlay items."""
        if scalebar is None:
            scalebar = self.options.overlay_items["scalebar"]
        if colorbar is None:
            colorbar = self.options.overlay_items["colorbar"]

        self.scalebar.setVisible(scalebar)
        self.colorbar.setVisible(colorbar)
