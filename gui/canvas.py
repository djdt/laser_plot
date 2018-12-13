from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from util.laserimage import plotLaserImage
from util.plothelpers import coords2value
from util.formatter import formatIsotopeTex


class Canvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.fig = Figure(frameon=False, tight_layout=True,
                          figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.image = None

        super().__init__(self.fig)
        self.setParent(parent)
        self.setStyleSheet("background-color:transparent;")
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)

        self.mpl_connect("motion_notify_event", self.updateStatusBar)
        self.mpl_connect("axes_leave_event", self.clearStatusBar)

    def close(self):
        self.mpl_disconncet("motion_notify_event")
        self.mpl_disconncet("axes_leave_event")
        self.clearStatusBar()
        super().close()

    def plot(self, laser, isotope, viewconfig):
        self.image = plotLaserImage(
            self.fig,
            self.ax,
            laser.get(isotope, calibrated=True, trimmed=True),
            colorbar="bottom",
            colorbarlabel=laser.calibration["units"].get(isotope, ""),
            label=formatIsotopeTex(isotope),
            fontsize=viewconfig["fontsize"],
            cmap=viewconfig["cmap"],
            interpolation=viewconfig["interpolation"],
            vmin=viewconfig["cmap_range"][0],
            vmax=viewconfig["cmap_range"][1],
            aspect=laser.aspect(),
            extent=laser.extent(trimmed=True),
        )
        self.draw()

    def clear(self):
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)

    def updateStatusBar(self, e):
        if e.inaxes == self.ax:
            x, y = e.xdata, e.ydata
            v = coords2value(self.image, x, y)
            self.window().statusBar().showMessage(f"{x:.2f},{y:.2f} [{v}]")

    def clearStatusBar(self, e):
        self.window().statusBar().clearMessage()

    def sizeHint(self):
        w, h = self.get_width_height()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        return QtCore.QSize(250, 250)