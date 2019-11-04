import copy
import numpy as np

from PySide2 import QtCore, QtGui, QtWidgets

from matplotlib.text import Text
from matplotlib.colors import LinearSegmentedColormap

from pew import Calibration, Config
from pew.srr import SRRConfig

from pewpew.lib import colocal
from pewpew.lib.calc import normalise
from pewpew.lib.viewoptions import ViewOptions
from pewpew.widgets.canvases import BasicCanvas
from pewpew.validators import (
    DecimalValidator,
    DecimalValidatorNoZero,
    PercentOrDecimalValidator,
)

from typing import Dict, List, Tuple, Union


class ApplyDialog(QtWidgets.QDialog):

    applyPressed = QtCore.Signal(QtCore.QObject)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_buttons = QtWidgets.QHBoxLayout()

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Ok
            | QtWidgets.QDialogButtonBox.Apply,
            self,
        )
        self.button_box.clicked.connect(self.buttonClicked)
        self.layout_buttons.addWidget(self.button_box)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.layout_main)
        layout.addLayout(self.layout_buttons)
        self.setLayout(layout)

    def buttonClicked(self, button: QtWidgets.QAbstractButton) -> None:
        sb = self.button_box.standardButton(button)

        if sb == QtWidgets.QDialogButtonBox.Apply:
            self.apply()
            self.applyPressed.emit(self)
        elif sb == QtWidgets.QDialogButtonBox.Ok:
            self.apply()
            self.applyPressed.emit(self)
            self.accept()
        else:
            self.reject()

    def apply(self) -> None:
        pass

    def isComplete(self) -> bool:
        return True

    @QtCore.Slot()
    def completeChanged(self) -> None:
        enabled = self.isComplete()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled)
        self.button_box.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(enabled)


class CalibrationDialog(ApplyDialog):
    calibrationSelected = QtCore.Signal(dict)
    calibrationApplyAll = QtCore.Signal(dict)

    def __init__(
        self,
        calibrations: Dict[str, Calibration],
        current_isotope: str,
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Calibration")
        self.calibrations = copy.deepcopy(calibrations)

        # LIne edits
        self.lineedit_gradient = QtWidgets.QLineEdit()
        self.lineedit_gradient.setValidator(DecimalValidatorNoZero(-1e10, 1e10, 4))
        self.lineedit_gradient.setPlaceholderText("1.0000")
        self.lineedit_intercept = QtWidgets.QLineEdit()
        self.lineedit_intercept.setValidator(DecimalValidator(-1e10, 1e10, 4))
        self.lineedit_intercept.setPlaceholderText("0.0000")
        self.lineedit_unit = QtWidgets.QLineEdit()
        self.lineedit_unit.setPlaceholderText("")

        # Isotope combo
        self.combo_isotopes = QtWidgets.QComboBox()
        self.combo_isotopes.addItems(list(self.calibrations.keys()))
        self.combo_isotopes.setCurrentText(current_isotope)
        self.previous_index = self.combo_isotopes.currentIndex()
        self.combo_isotopes.currentIndexChanged.connect(self.comboChanged)

        # Check all
        self.check_all = QtWidgets.QCheckBox("Apply config to all images.")

        # Button to plot
        self.button_plot = QtWidgets.QPushButton("Plot")
        self.button_plot.setEnabled(
            self.calibrations[current_isotope].points is not None
        )
        self.button_plot.pressed.connect(self.showCurve)

        layout_isotopes = QtWidgets.QHBoxLayout()
        layout_isotopes.addWidget(self.button_plot, 0, QtCore.Qt.AlignLeft)
        layout_isotopes.addWidget(self.combo_isotopes, 0, QtCore.Qt.AlignRight)

        # Form layout for line edits
        layout_form = QtWidgets.QFormLayout()
        layout_form.addRow("Gradient:", self.lineedit_gradient)
        layout_form.addRow("Intercept:", self.lineedit_intercept)
        layout_form.addRow("Unit:", self.lineedit_unit)

        self.layout_main.addLayout(layout_form)
        self.layout_main.addLayout(layout_isotopes)
        self.layout_main.addWidget(self.check_all)

        self.updateLineEdits()

    def updateLineEdits(self) -> None:
        name = self.combo_isotopes.currentText()

        gradient = self.calibrations[name].gradient
        if gradient == 1.0:
            self.lineedit_gradient.clear()
        else:
            self.lineedit_gradient.setText(f"{gradient:.4f}")
        intercept = self.calibrations[name].intercept
        if intercept == 0.0:
            self.lineedit_intercept.clear()
        else:
            self.lineedit_intercept.setText(f"{intercept:.4f}")
        unit = self.calibrations[name].unit
        if unit is None:
            self.lineedit_unit.clear()
        else:
            self.lineedit_unit.setText(str(unit))

    def updateCalibration(self, name: str) -> None:
        gradient = self.lineedit_gradient.text()
        intercept = self.lineedit_intercept.text()
        unit = self.lineedit_unit.text()

        if gradient != "":
            self.calibrations[name].gradient = float(gradient)
        if intercept != "":
            self.calibrations[name].intercept = float(intercept)
        if unit != "":
            self.calibrations[name].unit = unit

    def comboChanged(self) -> None:
        previous = self.combo_isotopes.itemText(self.previous_index)
        self.updateCalibration(previous)
        self.updateLineEdits()
        self.previous_index = self.combo_isotopes.currentIndex()
        self.button_plot.setEnabled(
            self.calibrations[self.combo_isotopes.currentText()].points is not None
        )

    def showCurve(self) -> None:
        dlg = CalibrationCurveDialog(
            self.calibrations[self.combo_isotopes.currentText()], parent=self
        )
        dlg.show()

    def apply(self) -> None:
        self.updateCalibration(self.combo_isotopes.currentText())
        if self.check_all.isChecked():
            self.calibrationApplyAll.emit(self.calibrations)
        else:
            self.calibrationSelected.emit(self.calibrations)


class CalibrationCurveDialog(QtWidgets.QDialog):
    def __init__(self, calibration: Calibration, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Calibration Curve")
        self.canvas = BasicCanvas(parent=self)
        ax = self.canvas.figure.subplots()

        x = calibration.concentrations()
        y = calibration.counts()
        x0, x1 = 0.0, np.nanmax(x) * 1.1

        m = calibration.gradient
        b = calibration.intercept

        xlabel = "Concentration"
        if calibration.unit != "":
            xlabel += f" ({calibration.unit})"

        ax.scatter(x, y, color="black")
        ax.plot([x0, x1], [m * x0 + b, m * x1 + b], ls=":", lw=1.5, color="black")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Counts")

        text = Text(
            x=0.05,
            y=0.95,
            text=str(calibration),
            transform=ax.transAxes,
            color="black",
            fontsize=12,
            horizontalalignment="left",
            verticalalignment="top",
        )

        ax.add_artist(text)

        self.canvas.draw()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def contextMenuEvent(self, event: QtCore.QEvent) -> None:
        context_menu = QtWidgets.QMenu(self)
        action_copy = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("insert-image"), "Copy Image", self
        )
        action_copy.setStatusTip("Copy image to clipboard.")
        action_copy.triggered.connect(self.canvas.copyToClipboard)
        context_menu.addAction(action_copy)
        context_menu.popup(event.globalPos())


class ColorRangeDialog(ApplyDialog):
    def __init__(
        self,
        viewoptions: ViewOptions,
        isotopes: List[str],
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(parent)
        self.default_range = viewoptions.colors.default_range
        self.ranges = copy.copy(viewoptions.colors._ranges)
        self.previous_isotope = isotopes[0] if len(isotopes) > 0 else None

        self.setWindowTitle("Colormap Range")

        self.lineedit_min = QtWidgets.QLineEdit()
        self.lineedit_min.setToolTip("Percentile for minium colormap value.")
        self.lineedit_min.setValidator(
            PercentOrDecimalValidator(-1e99, 1e99, parent=self.lineedit_min)
        )
        self.lineedit_max = QtWidgets.QLineEdit()
        self.lineedit_max.setValidator(
            PercentOrDecimalValidator(-1e99, 1e99, parent=self.lineedit_max)
        )
        self.lineedit_max.setToolTip("Percentile for maximum colormap value.")

        # Only add the isotopes combo if there are any open files
        self.combo_isotopes = QtWidgets.QComboBox()
        self.combo_isotopes.addItems(isotopes)
        self.combo_isotopes.setCurrentText(self.previous_isotope)
        self.combo_isotopes.currentIndexChanged.connect(self.comboChanged)
        self.combo_isotopes.setVisible(len(isotopes) > 0)

        # Checkbox
        self.check_all = QtWidgets.QCheckBox("Apply range to all elements.")
        self.check_all.setChecked(len(isotopes) == 0)
        self.check_all.setEnabled(len(isotopes) > 0)
        self.check_all.clicked.connect(self.enableComboIsotope)

        layout_form = QtWidgets.QFormLayout()
        layout_form.addRow("Minimum:", self.lineedit_min)
        layout_form.addRow("Maximum:", self.lineedit_max)

        self.layout_main.addLayout(layout_form)
        self.layout_main.addWidget(self.combo_isotopes, 0, QtCore.Qt.AlignRight)
        self.layout_main.addWidget(self.check_all)

        self.updateLineEdits()

    def enableComboIsotope(self, enabled: bool) -> None:
        self.combo_isotopes.setEnabled(not enabled)
        self.updateLineEdits()

    def updateLineEdits(self) -> None:
        self.lineedit_min.setPlaceholderText(str(self.default_range[0]))
        self.lineedit_max.setPlaceholderText(str(self.default_range[1]))
        tmin, tmax = "", ""

        # If the combobox is disabled then shown default range as true text
        if self.combo_isotopes.isEnabled():
            tmin, tmax = "", ""
        else:
            tmin, tmax = str(self.default_range[0]), str(self.default_range[1])

        # If there is a current isotope then update text to it's value, if exists
        current_isotope = self.combo_isotopes.currentText()
        if current_isotope in self.ranges:
            range = self.ranges[current_isotope]
            tmin, tmax = str(range[0]), str(range[1])

        self.lineedit_min.setText(tmin)
        self.lineedit_max.setText(tmax)

    def comboChanged(self) -> None:
        self.updateRange(self.previous_isotope)
        self.updateLineEdits()
        self.previous_isotope = self.combo_isotopes.currentText()

    def updateRange(self, isotope: str = None) -> None:
        tmin, tmax = self.lineedit_min.text(), self.lineedit_max.text()
        vmin, vmax = self.ranges.get(isotope, self.default_range)

        if tmin != "":
            vmin = tmin if "%" in tmin else float(tmin)
        if tmax != "":
            vmax = tmax if "%" in tmax else float(tmax)

        # Unless at least one value is set return
        if tmin == "" and tmax == "":
            return

        if isotope is not None:
            self.ranges[isotope] = (vmin, vmax)
        else:
            self.default_range = (vmin, vmax)

    def apply(self) -> None:
        current_isotope = self.combo_isotopes.currentText()
        self.updateRange(current_isotope if self.combo_isotopes.isEnabled() else None)


class ColocalisationDialog(QtWidgets.QDialog):
    def __init__(
        self,
        data: np.ndarray,
        mask: np.ndarray = None,
        colors: List[Tuple[float, ...]] = None,
        parent: QtWidgets.QWidget = None,
    ):
        assert data.dtype.names is not None
        super().__init__(parent)
        self.setWindowTitle("Colocalisation")
        self.data = data
        self.mask = mask

        if colors is None:
            colors = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        self.cmap = LinearSegmentedColormap.from_list("colocal_cmap", colors)

        self.canvas = BasicCanvas(figsize=(5, 5))
        self.canvas.ax = self.canvas.figure.add_subplot(facecolor="black")

        self.combo_name1 = QtWidgets.QComboBox()
        self.combo_name1.addItems(data.dtype.names)
        self.combo_name1.currentIndexChanged.connect(self.refresh)

        self.combo_name2 = QtWidgets.QComboBox()
        self.combo_name2.addItems(data.dtype.names)
        self.combo_name2.setCurrentIndex(1)
        self.combo_name2.currentIndexChanged.connect(self.refresh)

        self.label_r = QtWidgets.QLabel()
        self.label_p = QtWidgets.QLabel()
        self.label_icq = QtWidgets.QLabel()
        self.label_m1 = QtWidgets.QLabel()
        self.label_m2 = QtWidgets.QLabel()

        self.button_p = QtWidgets.QPushButton("Calculate ρ")
        self.button_p.pressed.connect(self.calculatePearsonsProbablity)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.close)

        layout_combos = QtWidgets.QHBoxLayout()
        layout_combos.addWidget(QtWidgets.QLabel("1:"))
        layout_combos.addWidget(self.combo_name1)
        layout_combos.addWidget(QtWidgets.QLabel("2:"))
        layout_combos.addWidget(self.combo_name2)

        group_li = QtWidgets.QGroupBox("Li")
        layout_li = QtWidgets.QFormLayout()
        layout_li.addRow("ICQ:", self.label_icq)
        group_li.setLayout(layout_li)

        group_pearson = QtWidgets.QGroupBox("Pearson")
        layout_pearson = QtWidgets.QFormLayout()
        layout_pearson.addRow("r:", self.label_r)
        layout_pearson.addRow("ρ:", self.label_p)
        layout_pearson.addWidget(self.button_p)
        group_pearson.setLayout(layout_pearson)

        group_manders = QtWidgets.QGroupBox("Manders")
        layout_manders = QtWidgets.QFormLayout()
        layout_manders.addRow("M1:", self.label_m1)
        layout_manders.addRow("M2:", self.label_m2)
        group_manders.setLayout(layout_manders)

        layout_vert = QtWidgets.QVBoxLayout()
        layout_vert.addStretch(1)
        layout_vert.addWidget(group_pearson)
        layout_vert.addWidget(group_manders)
        layout_vert.addWidget(group_li)
        layout_vert.addLayout(layout_combos)

        layout_horz = QtWidgets.QHBoxLayout()
        layout_horz.addLayout(layout_vert)
        layout_horz.addWidget(self.canvas)

        layout_main = QtWidgets.QVBoxLayout()
        layout_main.addLayout(layout_horz)
        layout_main.addWidget(self.button_box)
        self.setLayout(layout_main)

        self.refresh()

    def refresh(self) -> None:
        data1 = self.data[self.combo_name1.currentText()]
        data2 = self.data[self.combo_name2.currentText()]
        if self.mask is not None:
            data1, data2 = data1[self.mask], data2[self.mask]

        data1, data2 = normalise(data1), normalise(data2)

        # Pearson
        r = colocal.pearsonr(data1, data2)

        # Li
        icq = colocal.li_icq(data1, data2)

        # Choose a more approriate threshold?
        t1, a, b = colocal.costes_threshold(data1, data2)
        t2 = a * t1 + b
        m1, m2 = colocal.manders(
            data1, data2, t2, t1
        )  # Pass thresholds backwards as per Costes

        self.label_r.setText(f"{r:.2f}")
        self.label_p.setText("")
        self.label_icq.setText(f"{icq:.2f}")
        self.label_m1.setText(f"{m1:.2f}")
        self.label_m2.setText(f"{m2:.2f}")

        self.button_p.setEnabled(True)

        self.plot(data1, data2, t1, t2, a, b)

    def calculatePearsonsProbablity(self) -> None:
        d1 = self.data[self.combo_name1.currentText()]
        d2 = self.data[self.combo_name2.currentText()]

        _r, p = colocal.pearsonr_probablity(d1, d2, mask=self.mask, n=500)
        self.label_p.setText(f"{p:.2f}")

        self.button_p.setEnabled(False)

    def plot(
        self,
        data1: np.ndarray,
        data2: np.ndarray,
        t1: float,
        t2: float,
        a: float,
        b: float,
    ) -> None:
        self.canvas.ax.clear()

        x, y = data1.ravel(), data2.ravel()

        # Line points
        x1, y1 = (1, a + b) if a + b < 1 else ((1 - b) / a, 1)

        self.canvas.ax.scatter(
            x, y, s=1, marker=",", c=x - y, vmin=-0.5, vmax=0.5, cmap="RdYlGn"
        )
        self.canvas.ax.plot([0, x1], [b, y1], c="white", lw=1.0)
        self.canvas.ax.axhline(t2, c="white", ls=":", lw=1.0)
        self.canvas.ax.axvline(t1, c="white", ls=":", lw=1.0)

        self.canvas.ax.set_xlim(-0.05, 1.05)
        self.canvas.ax.set_ylim(-0.05, 1.05)
        self.canvas.ax.set_xlabel(self.combo_name1.currentText())
        self.canvas.ax.set_ylabel(self.combo_name2.currentText())

        self.canvas.draw_idle()


class ConfigDialog(ApplyDialog):
    configSelected = QtCore.Signal(Config)
    configApplyAll = QtCore.Signal(Config)

    def __init__(self, config: Config, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.config = copy.copy(config)

        # Line edits
        self.lineedit_spotsize = QtWidgets.QLineEdit()
        self.lineedit_spotsize.setText(str(self.config.spotsize))
        self.lineedit_spotsize.setValidator(DecimalValidator(0, 1e5, 1))
        self.lineedit_spotsize.textChanged.connect(self.completeChanged)
        self.lineedit_speed = QtWidgets.QLineEdit()
        self.lineedit_speed.setText(str(self.config.speed))
        self.lineedit_speed.setValidator(DecimalValidator(0, 1e5, 1))
        self.lineedit_speed.textChanged.connect(self.completeChanged)
        self.lineedit_scantime = QtWidgets.QLineEdit()
        self.lineedit_scantime.setText(str(self.config.scantime))
        self.lineedit_scantime.setValidator(DecimalValidator(0, 1e5, 4))
        self.lineedit_scantime.textChanged.connect(self.completeChanged)

        if isinstance(config, SRRConfig):
            self.lineedit_warmup = QtWidgets.QLineEdit()
            self.lineedit_warmup.setText(str(self.config.warmup))
            self.lineedit_warmup.setValidator(DecimalValidator(0, 1e3, 1))
            self.lineedit_warmup.textChanged.connect(self.completeChanged)
            self.spinbox_offsets = QtWidgets.QSpinBox()
            self.spinbox_offsets.setRange(2, 10)
            self.spinbox_offsets.setValue(self.config._subpixel_size)

        self.check_all = QtWidgets.QCheckBox("Apply config to all images.")

        # Form layout for line edits
        layout_form = QtWidgets.QFormLayout()
        layout_form.addRow("Spotsize (μm):", self.lineedit_spotsize)
        layout_form.addRow("Speed (μm):", self.lineedit_speed)
        layout_form.addRow("Scantime (s):", self.lineedit_scantime)
        if isinstance(config, SRRConfig):
            layout_form.addRow("Warmup (s):", self.lineedit_warmup)
            layout_form.addRow("Subpixel width:", self.spinbox_offsets)

        self.layout_main.addLayout(layout_form)
        self.layout_main.addWidget(self.check_all)

    def updateConfig(self) -> None:
        self.config.spotsize = float(self.lineedit_spotsize.text())
        self.config.speed = float(self.lineedit_speed.text())
        self.config.scantime = float(self.lineedit_scantime.text())
        if isinstance(self.config, SRRConfig):
            self.config.warmup = float(self.lineedit_warmup.text())
            self.config.set_equal_subpixel_offsets(self.spinbox_offsets.value())

    def apply(self) -> None:
        self.updateConfig()
        if self.check_all.isChecked():
            self.configApplyAll.emit(self.config)
        else:
            self.configSelected.emit(self.config)

    def isComplete(self) -> bool:
        if not self.lineedit_spotsize.hasAcceptableInput():
            return False
        if not self.lineedit_speed.hasAcceptableInput():
            return False
        if not self.lineedit_scantime.hasAcceptableInput():
            return False
        if isinstance(self.config, SRRConfig):
            if not self.lineedit_warmup.hasAcceptableInput():
                return False
        return True


class MultipleDirDialog(QtWidgets.QFileDialog):
    def __init__(self, parent: QtWidgets.QWidget, title: str, directory: str):
        super().__init__(parent, title, directory)
        self.setFileMode(QtWidgets.QFileDialog.Directory)
        self.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        self.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
        children = self.findChildren(QtWidgets.QListView)
        children.extend(self.findChildren(QtWidgets.QTreeView))
        for view in children:
            if isinstance(view.model(), QtWidgets.QFileSystemModel):
                view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    @staticmethod
    def getExistingDirectories(
        parent: QtWidgets.QWidget, title: str, directory: str
    ) -> List[str]:
        dlg = MultipleDirDialog(parent, title, directory)
        if dlg.exec():
            return list(dlg.selectedFiles())
        else:
            return []


class StatsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        data: np.ndarray,
        pixel_area: float,
        range: Tuple[Union[str, float], Union[str, float]],
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Statistics")

        self.canvas = BasicCanvas(figsize=(6, 2))
        self.canvas.ax = self.canvas.figure.add_subplot()

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.close)

        stats_left = QtWidgets.QFormLayout()
        stats_left.addRow("Shape:", QtWidgets.QLabel(str(data.shape)))
        stats_left.addRow("Size:", QtWidgets.QLabel(str(data.size)))
        stats_left.addRow(
            "Area:", QtWidgets.QLabel(f"{data.size * pixel_area:.4g} μm²")
        )

        # Discard shape and ensure no nans
        data = data[~np.isnan(data)].ravel()

        stats_right = QtWidgets.QFormLayout()
        stats_right.addRow("Min:", QtWidgets.QLabel(f"{np.min(data):.4g}"))
        stats_right.addRow("Max:", QtWidgets.QLabel(f"{np.max(data):.4g}"))
        stats_right.addRow("Mean:", QtWidgets.QLabel(f"{np.mean(data):.4g}"))
        stats_right.addRow("Median:", QtWidgets.QLabel(f"{np.ma.median(data):.4g}"))

        stats_box = QtWidgets.QGroupBox()
        stats_layout = QtWidgets.QHBoxLayout()
        stats_layout.addLayout(stats_left)
        stats_layout.addLayout(stats_right)
        stats_box.setLayout(stats_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(stats_box)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        # Calculate the range
        vmin, vmax = range
        plot_data = data[np.logical_and(data >= vmin, data <= vmax)]
        self.plot(plot_data)

    def contextMenuEvent(self, event: QtCore.QEvent) -> None:
        action_copy_image = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("insert-image"), "Copy Image", self
        )
        action_copy_image.setStatusTip("Copy image to clipboard.")
        action_copy_image.triggered.connect(self.canvas.copyToClipboard)

        context_menu = QtWidgets.QMenu(self)
        context_menu.addAction(action_copy_image)
        context_menu.popup(event.globalPos())

    def plot(self, data: np.ndarray) -> None:
        highlight = self.palette().color(QtGui.QPalette.Highlight).name()
        self.canvas.ax.hist(data.ravel(), bins="auto", color=highlight)
        self.canvas.draw()
