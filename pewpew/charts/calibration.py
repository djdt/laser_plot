from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCharts import QtCharts

import numpy as np

from pewpew.charts.base import BaseChart
from pewpew.charts.colors import light_theme, sequential, highlights

from pewpew.lib.numpyqt import array_to_polygonf


class CalibrationChart(BaseChart):
    """BaseChart for displaying a calibration curve.

    To use call setPoints, setLine and setText.
    Hovering calibration points reveals their values.
    """

    def __init__(self, title: str = None, parent: QtWidgets.QWidget = None):
        super().__init__(QtCharts.QChart(), theme=light_theme, parent=parent)
        self.setRubberBand(QtCharts.QChartView.RectangleRubberBand)
        self.setMinimumSize(QtCore.QSize(640, 480))
        self.setRenderHint(QtGui.QPainter.Antialiasing)

        if title is not None:
            self.chart().setTitle(title)

        self.chart().legend().hide()

        self.xaxis = QtCharts.QValueAxis()
        self.yaxis = QtCharts.QValueAxis()

        self.addAxis(self.xaxis, QtCore.Qt.AlignBottom)
        self.addAxis(self.yaxis, QtCore.Qt.AlignLeft)

        self.label_series = QtCharts.QScatterSeries()
        self.label_series.append(0, 0)
        self.label_series.setBrush(QtGui.QBrush(QtCore.Qt.black, QtCore.Qt.NoBrush))
        self.label_series.setPointLabelsFormat("(@xPoint, @yPoint)")
        self.label_series.setPointLabelsColor(light_theme["text"])
        self.label_series.setVisible(False)

        self.chart().addSeries(self.label_series)
        self.label_series.attachAxis(self.xaxis)
        self.label_series.attachAxis(self.yaxis)

        self.line = QtCharts.QLineSeries()
        self.line.setPen(QtGui.QPen(sequential[1], 1.5))
        # self.line.setColor(QtCore.Qt.red)

        self.chart().addSeries(self.line)
        self.line.attachAxis(self.xaxis)
        self.line.attachAxis(self.yaxis)

        self.series = QtCharts.QScatterSeries()
        self.series.setPen(QtGui.QPen(sequential[1], 1.5))
        self.series.setBrush(QtGui.QBrush(highlights[1]))
        self.series.setMarkerSize(12)

        self.chart().addSeries(self.series)
        self.series.attachAxis(self.xaxis)
        self.series.attachAxis(self.yaxis)

        self.series.hovered.connect(self.showPointPosition)

        self.label = QtWidgets.QGraphicsTextItem()
        self.label.setPlainText("hats")
        self.label.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
        self.chart().scene().addItem(self.label)
        self.chart().plotAreaChanged.connect(self.moveLabel)

    def moveLabel(self, rect: QtCore.QRectF) -> None:
        self.label.setPos(rect.topLeft())

    def setPoints(self, points: np.ndarray) -> None:
        if not (points.ndim == 2 and points.shape[1] == 2):  # pragma: no cover
            raise ValueError("points must have shape (n, 2).")

        xmin, xmax = np.amin(points[:, 0]), np.amax(points[:, 0])
        ymin, ymax = np.amin(points[:, 1]), np.amax(points[:, 1])

        self.xaxis.setRange(xmin, xmax)
        self.yaxis.setRange(ymin, ymax)

        poly = array_to_polygonf(points)
        self.series.replace(poly)

        self.xaxis.applyNiceNumbers()
        self.yaxis.applyNiceNumbers()

    def setLine(self, x0: float, x1: float, gradient: float, intercept: float) -> None:
        self.line.replace(
            [
                QtCore.QPointF(x0, gradient * x0 + intercept),
                QtCore.QPointF(x1, gradient * x1 + intercept),
            ]
        )

    def setText(self, text: str) -> None:
        self.label.setPlainText(text)

    def showPointPosition(self, point: QtCore.QPointF, state: bool):
        self.label_series.setVisible(state)
        self.label_series.setPointLabelsVisible(state)
        if state:
            self.label_series.replace(0, point.x(), point.y())

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.RightButton:
            self.chart().zoomReset()
        else:
            super().mouseReleaseEvent(event)
        self.xaxis.applyNiceNumbers()
        self.yaxis.applyNiceNumbers()
