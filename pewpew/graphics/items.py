from PySide2 import QtCore, QtGui, QtWidgets

import numpy as np

from pewpew.graphics.util import polygonf_contains_points

from pewpew.lib.numpyqt import array_to_image, polygonf_to_array

from typing import Dict, Generator


class ResizeableRectItem(QtWidgets.QGraphicsRectItem):
    cursors = {
        "left": QtCore.Qt.SizeHorCursor,
        "right": QtCore.Qt.SizeHorCursor,
        "top": QtCore.Qt.SizeVerCursor,
        "bottom": QtCore.Qt.SizeVerCursor,
    }

    def __init__(
        self,
        rect: QtCore.QRectF,
        selection_dist: int,
        parent: QtWidgets.QGraphicsItem = None,
    ):
        super().__init__(rect, parent)
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable
            | QtWidgets.QGraphicsItem.ItemIsSelectable
            | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.selection_dist = selection_dist
        self.selectedEdge: str = None

    def edgeAt(self, pos: QtCore.QPointF) -> str:
        view = next(iter(self.scene().views()), None)
        if view is None:
            return None
        dist = (
            view.mapToScene(QtCore.QRect(0, 0, self.selection_dist, 1))
            .boundingRect()
            .width()
        )

        if pos.x() < self.rect().left() + dist:
            return "left"
        elif pos.x() > self.rect().right() - dist:
            return "right"
        elif pos.y() < self.rect().top() + dist:
            return "top"
        elif pos.y() > self.rect().bottom() - dist:
            return "bottom"
        else:
            return None

    def hoverMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self.isSelected():
            edge = self.edgeAt(event.pos())
            if edge in self.cursors:
                self.setCursor(self.cursors[edge])
            else:
                self.setCursor(QtCore.Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.setCursor(QtCore.Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self.isSelected():
            self.selectedEdge = self.edgeAt(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        pos = self.itemChange(QtWidgets.QGraphicsItem.ItemPositionChange, event.pos())
        if self.selectedEdge is None:
            super().mouseMoveEvent(event)
        else:
            rect = self.rect()
            if self.selectedEdge == "left" and pos.x() < rect.right():
                rect.setLeft(pos.x())
            elif self.selectedEdge == "right" and pos.x() > rect.left():
                rect.setRight(pos.x())
            elif self.selectedEdge == "top" and pos.y() < rect.bottom():
                rect.setTop(pos.y())
            elif self.selectedEdge == "bottom" and pos.y() > rect.top():
                rect.setBottom(pos.y())

            self.prepareGeometryChange()
            self.setRect(rect)


class ScaledImageItem(QtWidgets.QGraphicsItem):
    def __init__(
        self,
        image: QtGui.QImage,
        rect: QtCore.QRectF,
        smooth: bool = False,
        parent: QtWidgets.QGraphicsItem = None,
    ):
        super().__init__(parent)
        self.setCacheMode(
            QtWidgets.QGraphicsItem.DeviceCoordinateCache
        )  # Speed up redraw of image
        if smooth:
            self.image = image.scaledToHeight(
                image.height() * 2, QtCore.Qt.SmoothTransformation
            )
            self.scale = 2
        else:
            self.image = image
            self.scale = 1
        self.rect = QtCore.QRectF(rect)  # copy the rect

    def width(self) -> int:
        return self.image.width() // self.scale

    def height(self) -> int:
        return self.image.height() // self.scale

    def boundingRect(self) -> QtCore.QRectF:
        return self.rect

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget = None,
    ):
        painter.drawImage(self.rect, self.image)

    @classmethod
    def fromArray(
        cls,
        array: np.ndarray,
        rect: QtCore.QRectF,
        colortable: np.ndarray = None,
        smooth: bool = False,
        parent: QtWidgets.QGraphicsItem = None,
    ) -> "ScaledImageItem":
        image = array_to_image(array)
        if colortable is not None:
            image.setColorTable(colortable)
            image.setColorCount(len(colortable))
        item = cls(image, rect, smooth, parent=parent)
        return item


class SelectionItem(QtWidgets.QGraphicsObject):
    selectionChanged = QtCore.Signal(np.ndarray, "QStringList")

    def __init__(
        self,
        modes: Dict[QtCore.Qt.KeyboardModifier, str] = None,
        parent: QtWidgets.QGraphicsItem = None,
    ):
        super().__init__(parent)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setZValue(99)

        self.modes = modes or {}

    def modifierModes(
        self, modifiers: QtCore.Qt.KeyboardModifier
    ) -> Generator[str, None, None]:
        for k, v in self.modes.items():
            if k & modifiers:
                yield v


class ScaledImageSelectionItem(SelectionItem):
    def __init__(
        self,
        image: ScaledImageItem = None,
        modes: Dict[QtCore.Qt.KeyboardModifier, str] = None,
        parent: QtWidgets.QGraphicsItem = None,
    ):
        _modes = {QtCore.Qt.ShiftModifier: "add", QtCore.Qt.ControlModifier: "subtract"}
        if modes is not None:
            _modes.update(modes)
        super().__init__(modes=_modes, parent=parent)

        self.rect = QtCore.QRectF(image.rect)
        self.image_shape = (image.height(), image.width())

    def pixelSize(self) -> QtCore.QSizeF:
        return QtCore.QSizeF(
            self.rect.width() / self.image_shape[1],
            self.rect.height() / self.image_shape[0],
        )

    def snapPos(self, pos: QtCore.QPointF) -> QtCore.QPointF:
        pixel = self.pixelSize()
        x = round(pos.x() / pixel.width()) * pixel.width()
        y = round(pos.y() / pixel.height()) * pixel.height()
        return QtCore.QPointF(x, y)


class LassoImageSelectionItem(ScaledImageSelectionItem):
    def __init__(
        self,
        image: ScaledImageItem,
        modes: Dict[QtCore.Qt.Modifier, str] = None,
        pen: QtGui.QPen = None,
        parent: QtWidgets.QGraphicsItem = None,
    ):
        super().__init__(image, parent=parent)

        if pen is None:
            pen = QtGui.QPen(QtCore.Qt.white, 2.0)

        self.pen = pen
        self.pen.setCosmetic(True)

        self.poly = QtGui.QPolygonF()

    def boundingRect(self) -> QtCore.QRectF:
        return self.poly.boundingRect()

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.addPolygon(self.poly)
        return path

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.poly.clear()
        self.poly.append(self.snapPos(event.pos()))

        self.prepareGeometryChange()

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if not event.buttons() & QtCore.Qt.LeftButton:
            return
        if self.poly.size() == 0:
            return
        pos = self.snapPos(event.pos())
        if self.poly.last() != pos:
            self.poly.append(pos)
            self.prepareGeometryChange()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        modes = list(self.modifierModes(event.modifiers()))
        pixel = self.pixelSize()

        array = polygonf_to_array(self.poly)
        # Get start and end points of area
        x1, x2 = np.amin(array[:, 0]), np.amax(array[:, 0])
        y1, y2 = np.amin(array[:, 1]), np.amax(array[:, 1])
        # Bound to image area
        x1, y1 = max(x1, 0.0), max(y1, 0.0)
        x2 = min(x2, self.rect.width() - pixel.width() / 2.0)
        y2 = min(y2, self.rect.height() - pixel.height() / 2.0)
        # Generate pixel centers
        xs = np.arange(x1, x2, pixel.width()) + pixel.width() / 2.0
        ys = np.arange(y1, y2, pixel.height()) + pixel.height() / 2.0
        X, Y = np.meshgrid(xs, ys)
        pixels = np.stack((X.flat, Y.flat), axis=1)

        # Get mask of selected area
        mask = np.zeros(self.image_shape, dtype=np.bool)
        polymask = polygonf_contains_points(self.poly, pixels).reshape(ys.size, xs.size)
        # Insert
        ix, iy = int(x1 / pixel.width()), int(y1 / pixel.height())
        mask[iy : iy + ys.size, ix : ix + xs.size] = polymask

        # self.poly.append(self.poly.first())
        self.poly.clear()
        self.prepareGeometryChange()

        self.selectionChanged.emit(mask, modes)

    def paint(
        self,
        painter: QtGui.QPainter,
        options: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget = None,
    ):
        painter.save()

        painter.setPen(self.pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.drawPolyline(self.poly)

        painter.restore()


class RectImageSelectionItem(ScaledImageSelectionItem):
    def __init__(
        self,
        image: ScaledImageItem,
        modes: Dict[QtCore.Qt.Modifier, str] = None,
        pen: QtGui.QPen = None,
        parent: QtWidgets.QGraphicsItem = None,
    ):
        super().__init__(image, parent=parent)

        if pen is None:
            pen = QtGui.QPen(QtCore.Qt.white, 2.0)

        self.pen = pen
        self.pen.setCosmetic(True)

        self._rect = QtCore.QRectF()

    def boundingRect(self) -> QtCore.QRectF:
        return self._rect.normalized()

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if not event.button() & QtCore.Qt.LeftButton:
            return
        self._rect.setTopLeft(event.pos())
        self._rect.setBottomRight(event.pos())
        self.prepareGeometryChange()

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if not event.buttons() & QtCore.Qt.LeftButton:
            return
        self._rect.setBottomRight(event.pos())
        self.prepareGeometryChange()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if not event.button() & QtCore.Qt.LeftButton:
            return
        modes = list(self.modifierModes(event.modifiers()))

        px, py = (
            self.rect.width() / self.image_shape[1],
            self.rect.height() / self.image_shape[0],
        )  # pixel size

        x1, y1, x2, y2 = self._rect.normalized().getCoords()
        x1 = np.round(x1 / px).astype(int)
        x2 = np.round(x2 / px).astype(int)
        y1 = np.round(y1 / py).astype(int)
        y2 = np.round(y2 / py).astype(int)

        mask = np.zeros(self.image_shape, dtype=np.bool)
        mask[y1:y2, x1:x2] = True

        self._rect = QtCore.QRectF()
        self.prepareGeometryChange()

        self.selectionChanged.emit(mask, modes)

    def paint(
        self,
        painter: QtGui.QPainter,
        options: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget = None,
    ):
        painter.save()

        painter.setPen(self.pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.drawRect(self._rect)

        painter.restore()