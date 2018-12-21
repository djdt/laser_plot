from PyQt5 import QtCore, QtGui, QtWidgets
import os.path

from gui.validators import PercentValidator


class OkApplyCancelDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Ok
            | QtWidgets.QDialogButtonBox.Apply,
            self,
        )
        self.button_box.clicked.connect(self.buttonClicked)

    def buttonClicked(self, button):
        sb = self.button_box.standardButton(button)

        if sb == QtWidgets.QDialogButtonBox.Apply:
            self.apply()
        elif sb == QtWidgets.QDialogButtonBox.Ok:
            self.accept()
        else:
            self.reject()

    def apply(self):
        pass


class ColorRangeDialog(OkApplyCancelDialog):
    def __init__(self, current_range, parent=None):
        self.range = current_range
        super().__init__(parent)
        self.setWindowTitle("Colormap Range")

        self.lineedit_min = QtWidgets.QLineEdit()
        self.lineedit_min.setPlaceholderText(str(current_range[0]))
        self.lineedit_min.setToolTip("Percentile for minium colormap value.")
        self.lineedit_min.setValidator(PercentValidator(parent=self.lineedit_min))
        self.lineedit_max = QtWidgets.QLineEdit()
        self.lineedit_max.setPlaceholderText(str(current_range[1]))
        self.lineedit_min.setValidator(PercentValidator(parent=self.lineedit_max))
        self.lineedit_max.setToolTip("Percentile for maximum colormap value.")

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Minimum:", self.lineedit_min)
        form_layout.addRow("Maximum:", self.lineedit_max)

        main_layout = QtWidgets.QVBoxLayout()

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def apply(self):
        min_text, max_text = self.lineedit_min.text(), self.lineedit_max.text()
        cmap_range = [
            min_text if min_text != "" else self.range[0],
            max_text if max_text != "" else self.range[1],
        ]
        self.parent().viewconfig["cmap_range"] = cmap_range
        self.parent().draw()

    def accept(self):
        min_text, max_text = self.lineedit_min.text(), self.lineedit_max.text()
        if min_text != "":
            self.range[0] = min_text
        if max_text != "":
            self.range[1] = max_text
        super().accept()


class CalibrationDialog(OkApplyCancelDialog):
    def __init__(self, calibration, current_isotope, isotopes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration")
        self.calibration = calibration

        # LIne edits
        self.lineedit_gradient = QtWidgets.QLineEdit()
        self.lineedit_gradient.setValidator(QtGui.QDoubleValidator(-1e10, 1e10, 4))
        self.lineedit_gradient.setPlaceholderText("1.0")
        self.lineedit_intercept = QtWidgets.QLineEdit()
        self.lineedit_intercept.setValidator(QtGui.QDoubleValidator(-1e10, 1e10, 4))
        self.lineedit_intercept.setPlaceholderText("0.0")
        self.lineedit_unit = QtWidgets.QLineEdit()
        self.lineedit_unit.setPlaceholderText("<None>")

        # Form layout for line edits
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Gradient:", self.lineedit_gradient)
        form_layout.addRow("Intercept:", self.lineedit_intercept)
        form_layout.addRow("Unit:", self.lineedit_unit)

        # Isotope combo
        self.combo_isotopes = QtWidgets.QComboBox()
        self.combo_isotopes.addItems(isotopes)
        self.previous_index = self.combo_isotopes.findText(current_isotope)
        self.combo_isotopes.setCurrentIndex(self.previous_index)
        self.combo_isotopes.currentIndexChanged.connect(self.comboChanged)

        # Dialog buttons
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.combo_isotopes, 1, QtCore.Qt.AlignRight)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

        self.updateLineEdits()

    def updateLineEdits(self):
        new = self.combo_isotopes.currentText()

        if new in self.calibration["gradients"]:
            self.lineedit_gradient.setText(str(self.calibration["gradients"][new]))
        else:
            self.lineedit_gradient.clear()
        if new in self.calibration["intercepts"]:
            self.lineedit_intercept.setText(str(self.calibration["intercepts"][new]))
        else:
            self.lineedit_intercept.clear()
        if new in self.calibration["units"]:
            self.lineedit_unit.setText(str(self.calibration["units"][new]))
        else:
            self.lineedit_unit.clear()

    def updateCalibration(self, isotope):
        gradient = self.lineedit_gradient.text()
        intercept = self.lineedit_intercept.text()
        unit = self.lineedit_unit.text()

        if gradient == "" or float(gradient) == 1.0:
            self.calibration["gradients"].pop(isotope, None)
        else:
            self.calibration["gradients"][isotope] = float(gradient)
        if intercept == "" or float(intercept) == 0.0:
            self.calibration["intercepts"].pop(isotope, None)
        else:
            self.calibration["intercepts"][isotope] = float(intercept)
        if unit == "":
            self.calibration["units"].pop(isotope, None)
        else:
            self.calibration["units"][isotope] = unit

    def comboChanged(self):
        previous = self.combo_isotopes.itemText(self.previous_index)
        self.updateCalibration(previous)
        self.updateLineEdits()
        self.previous_index = self.combo_isotopes.currentIndex()

    def apply(self):
        self.updateCalibration(self.combo_isotopes.currentText())
        self.parent().laser.calibration = self.calibration
        self.parent().draw()

    def accept(self):
        self.updateCalibration(self.combo_isotopes.currentText())
        super().accept()


class ConfigDialog(OkApplyCancelDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.spotsize = config["spotsize"]
        self.speed = config["speed"]
        self.scantime = config["scantime"]

        # Line edits
        self.lineedit_spotsize = QtWidgets.QLineEdit()
        self.lineedit_spotsize.setPlaceholderText(str(self.spotsize))
        self.lineedit_spotsize.setValidator(QtGui.QDoubleValidator(0, 1e3, 2))
        self.lineedit_speed = QtWidgets.QLineEdit()
        self.lineedit_speed.setPlaceholderText(str(self.speed))
        self.lineedit_speed.setValidator(QtGui.QDoubleValidator(0, 1e3, 2))
        self.lineedit_scantime = QtWidgets.QLineEdit()
        self.lineedit_scantime.setPlaceholderText(str(self.scantime))
        self.lineedit_scantime.setValidator(QtGui.QDoubleValidator(0, 1e3, 4))

        # Form layout for line edits
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Spotsize (μm):", self.lineedit_spotsize)
        form_layout.addRow("Speed (μm):", self.lineedit_speed)
        form_layout.addRow("Scantime (s):", self.lineedit_scantime)

        # Checkbox
        self.check_all = QtWidgets.QCheckBox("Apply config to all images.")
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.check_all)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def updateConfig(self):
        if self.lineedit_spotsize.text() != "":
            self.spotsize = float(self.lineedit_spotsize.text())
        if self.lineedit_speed.text() != "":
            self.speed = float(self.lineedit_speed.text())
        if self.lineedit_scantime.text() != "":
            self.scantime = float(self.lineedit_scantime.text())

    def apply(self):
        self.updateConfig()
        self.parent().laser.config["spotsize"] = self.spotsize
        self.parent().laser.config["speed"] = self.speed
        self.parent().laser.config["scantime"] = self.scantime
        self.parent().draw()

    def accept(self):
        self.updateConfig()
        super().accept()


class TrimDialog(OkApplyCancelDialog):
    def __init__(self, trim=[0, 0], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trim")
        self.trim = trim

        self.lineedit_left = QtWidgets.QLineEdit()
        self.lineedit_left.setPlaceholderText(str(trim[0]))
        self.lineedit_left.setValidator(QtGui.QIntValidator(0, 1e9))
        self.lineedit_right = QtWidgets.QLineEdit()
        self.lineedit_right.setPlaceholderText(str(trim[1]))
        self.lineedit_right.setValidator(QtGui.QIntValidator(0, 1e9))

        self.combo_trim = QtWidgets.QComboBox()
        self.combo_trim.addItems(["rows", "s", "μm"])
        self.combo_trim.setCurrentIndex(1)
        self.combo_trim.currentIndexChanged.connect(self.comboTrim)

        layout_trim = QtWidgets.QHBoxLayout()
        layout_trim.addWidget(QtWidgets.QLabel("Left:"))
        layout_trim.addWidget(self.lineedit_left)
        layout_trim.addWidget(QtWidgets.QLabel("Right:"))
        layout_trim.addWidget(self.lineedit_right)
        layout_trim.addWidget(self.combo_trim)

        self.check_all = QtWidgets.QCheckBox("Apply trim to all images.")

        layout_main = QtWidgets.QVBoxLayout()
        layout_main.addLayout(layout_trim)
        layout_main.addWidget(self.check_all)
        layout_main.addWidget(self.button_box)
        self.setLayout(layout_main)

    def comboTrim(self):
        if self.combo_trim.currentText() == "rows":
            self.lineedit_left.setValidator(QtGui.QIntValidator(0, 1e9))
            self.lineedit_right.setValidator(QtGui.QIntValidator(0, 1e9))
        else:
            self.lineedit_left.setValidator(QtGui.QDoubleValidator(0, 1e9, 2))
            self.lineedit_right.setValidator(QtGui.QDoubleValidator(0, 1e9, 2))

    def updateTrim(self):
        if self.lineedit_left.text() != "":
            self.trim[0] = float(self.lineedit_left.text())
        if self.lineedit_right.text() != "":
            self.trim[1] = float(self.lineedit_right.text())

    def apply(self):
        self.updateTrim()
        self.parent().laser.setTrim(self.trim, self.combo_trim.currentText())
        self.parent().draw()

    def accept(self):
        self.updateTrim()
        super().accept()


class ExportDialog(QtWidgets.QDialog):
    def __init__(
        self, name, source, current_isotope, num_isotopes=1, num_layers=1, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.current_isotope = current_isotope
        self.num_isotopes = num_isotopes
        self.num_layers = num_layers

        default_name = os.path.join(os.path.dirname(source), name) + ".csv"

        self.lineedit_file = QtWidgets.QLineEdit(default_name)
        self.lineedit_file.setMinimumWidth(300)
        self.lineedit_file.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum
        )
        self.lineedit_file.textEdited.connect(self.inputChanged)
        button_file = QtWidgets.QPushButton("Select...")
        button_file.pressed.connect(self.onButtonFile)

        file_layout = QtWidgets.QHBoxLayout()
        file_layout.addWidget(self.lineedit_file)
        file_layout.addWidget(button_file)

        self.check_isotopes = QtWidgets.QCheckBox("Save all isotopes.")
        self.check_isotopes.stateChanged.connect(self.inputChanged)
        if self.num_isotopes < 2:
            self.check_isotopes.setEnabled(False)
        self.check_layers = QtWidgets.QCheckBox("Save all layers.")
        self.check_layers.stateChanged.connect(self.inputChanged)
        if self.num_layers < 2:
            self.check_layers.setEnabled(False)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        label_preview = QtWidgets.QLabel("Preview: ")
        self.lineedit_preview = QtWidgets.QLineEdit()
        self.lineedit_preview.setEnabled(False)
        self.redrawPreview()

        preview_layout = QtWidgets.QHBoxLayout()
        preview_layout.addWidget(label_preview)
        preview_layout.addWidget(self.lineedit_preview)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(file_layout)
        main_layout.addWidget(self.check_isotopes)
        main_layout.addWidget(self.check_layers)
        main_layout.addLayout(preview_layout)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def getPath(self, isotope=None, layer=None):
        path, ext = os.path.splitext(self.lineedit_file.text())
        if isotope is not None:
            path += f"_{isotope}"
        if layer is not None:
            path += f"_layer{layer}"
        return path + ext

    def onButtonFile(self):
        filter = "CSV files(*.csv);;Numpy archives(*.npz);;" "PNG images(*.png);;"
        if self.num_layers > 1:
            filter += "Rectilinear VTKs(*.vtr);;"
        filter += "All files(*)"
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export As",
            self.lineedit_file.text(),
            filter,
            "CSV files(*.csv)",
            QtWidgets.QFileDialog.DontConfirmOverwrite,
        )
        if path:
            self.lineedit_file.setText(path)
            self.inputChanged()

    def inputChanged(self):
        self.updateChecks()
        self.redrawPreview()

    def updateChecks(self):
        ext = os.path.splitext(self.lineedit_file.text())[1].lower()

        if ext == ".vtr":
            if self.check_isotopes.isEnabled():
                self.check_isotopes.setEnabled(False)
                self.check_isotopes.setChecked(False)
            if self.check_layers.isEnabled():
                self.check_layers.setEnabled(False)
                self.check_layers.setChecked(False)
        elif ext == ".npz":
            if self.check_isotopes.isEnabled():
                self.check_isotopes.setEnabled(False)
                self.check_isotopes.setChecked(False)
            if self.check_layers.isEnabled():
                self.check_layers.setEnabled(False)
                self.check_layers.setChecked(False)
        else:
            if self.num_isotopes > 1:
                self.check_isotopes.setEnabled(True)
            if self.num_layers > 1:
                self.check_layers.setEnabled(True)

    def redrawPreview(self):
        path = self.getPath(
            isotope=self.current_isotope if self.check_isotopes.isChecked() else None,
            layer=1 if self.check_layers.isChecked() else None,
        )
        if not os.path.isdir(path):
            path = os.path.basename(path)
        self.lineedit_preview.setText(path)
