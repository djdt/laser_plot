import os.path
import copy

from PyQt5 import QtCore, QtGui, QtWidgets

from pewpew.ui.widgets import Canvas, OverwriteFilePrompt
from pewpew.ui.dialogs import CalibrationDialog, ConfigDialog, StatsDialog
from pewpew.ui.dialogs.export import CSVExportDialog, PNGExportDialog

from pewpew.lib import io

from pewpew.lib.laser import Laser
from pewpew.ui.dialogs import ApplyDialog
from pewpew.ui.dialogs.export import ExportDialog


# TODO fix tab names


class ImageDockTitleBar(QtWidgets.QWidget):

    nameChanged = QtCore.pyqtSignal("QString")

    def __init__(self, title: str, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.title = QtWidgets.QLabel(title)
        # self.parent().windowTitleChanged.connect(self.setTitle)

        # Button Bar
        self.button_close = QtWidgets.QPushButton(
            QtGui.QIcon.fromTheme("edit-delete"), ""
        )
        self.button_close.setToolTip("Close the image.")
        self.button_zoom = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("zoom-in"), "")
        self.button_zoom.setToolTip("Zoom into slected area.")
        self.button_zoom_original = QtWidgets.QPushButton(
            QtGui.QIcon.fromTheme("zoom-original"), ""
        )
        self.button_zoom_original.setToolTip("Reset to original zoom.")

        layout_buttons = QtWidgets.QHBoxLayout()
        layout_buttons.addWidget(self.button_zoom, QtCore.Qt.AlignRight)
        layout_buttons.addWidget(self.button_zoom_original, QtCore.Qt.AlignRight)
        layout_buttons.addWidget(self.button_close, QtCore.Qt.AlignRight)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.title, 1)
        layout.addLayout(layout_buttons, 0)

        self.setLayout(layout)

    def setTitle(self, title: str) -> None:
        if "&" not in title:
            self.title.setText(title)

    def mouseDoubleClickEvent(self, event: QtCore.QEvent) -> None:
        if self.title.underMouse():
            name, ok = QtWidgets.QInputDialog.getText(
                self, "Rename", "Name:", QtWidgets.QLineEdit.Normal, self.title.text()
            )
            if ok:
                self.nameChanged.emit(name)


class LaserImageDock(QtWidgets.QDockWidget):
    def __init__(self, laser: Laser, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setFeatures(
            QtWidgets.QDockWidget.DockWidgetClosable
            | QtWidgets.QDockWidget.DockWidgetMovable
        )

        self.laser = laser
        self.canvas = Canvas(parent=self)

        self.combo_isotope = QtWidgets.QComboBox()
        self.combo_isotope.currentIndexChanged.connect(self.onComboIsotope)
        self.combo_isotope.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.populateComboIsotopes()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.combo_isotope, 1, QtCore.Qt.AlignRight)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

        # Title bar
        self.title_bar = ImageDockTitleBar("", self)
        self.title_bar.nameChanged.connect(self.titleNameChanged)
        self.windowTitleChanged.connect(self.title_bar.setTitle)
        self.setTitleBarWidget(self.title_bar)
        self.setWindowTitle(self.laser.name)

        self.title_bar.button_zoom.clicked.connect(self.canvas.startZoom)
        self.title_bar.button_zoom_original.clicked.connect(self.canvas.unzoom)
        self.title_bar.button_close.clicked.connect(self.onMenuClose)

        # Context menu actions
        self.action_copy = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("edit-copy"), "Open Copy", self
        )
        self.action_copy.setStatusTip("Open a copy of this data")
        self.action_copy.triggered.connect(self.onMenuCopy)
        self.action_save = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("document-save"), "Save", self
        )
        self.action_save.setStatusTip("Save data to archive.")
        self.action_save.triggered.connect(self.onMenuSave)

        self.action_export = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("document-save-as"), "Export", self
        )
        self.action_export.setStatusTip("Save data to different formats.")
        self.action_export.triggered.connect(self.onMenuExport)

        self.action_calibration = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("go-top"), "Calibration", self
        )
        self.action_calibration.setStatusTip("Edit image calibration.")
        self.action_calibration.triggered.connect(self.onMenuCalibration)

        self.action_config = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("document-edit"), "Config", self
        )
        self.action_config.setStatusTip("Edit image config.")
        self.action_config.triggered.connect(self.onMenuConfig)

        self.action_stats = QtWidgets.QAction(
            QtGui.QIcon.fromTheme(""), "Statistics", self
        )
        self.action_stats.setStatusTip("Data histogram and statistics.")
        self.action_stats.triggered.connect(self.onMenuStats)

        self.action_close = QtWidgets.QAction(
            QtGui.QIcon.fromTheme("edit-delete"), "Close", self
        )
        self.action_close.setStatusTip("Close the images.")
        self.action_close.triggered.connect(self.onMenuClose)

    def draw(self) -> None:
        self.canvas.clear()
        self.canvas.plot(
            self.laser, self.combo_isotope.currentText(), self.window().viewconfig
        )
        self.canvas.draw()

    def buildContextMenu(self) -> QtWidgets.QMenu:
        context_menu = QtWidgets.QMenu(self)
        context_menu.addAction(self.action_copy)
        context_menu.addSeparator()
        context_menu.addAction(self.action_save)
        context_menu.addAction(self.action_export)
        context_menu.addSeparator()
        context_menu.addAction(self.action_calibration)
        context_menu.addAction(self.action_config)
        context_menu.addAction(self.action_stats)
        context_menu.addSeparator()
        context_menu.addAction(self.action_close)
        return context_menu

    def populateComboIsotopes(self) -> None:
        isotopes = sorted(self.laser.isotopes())
        self.combo_isotope.blockSignals(True)
        self.combo_isotope.clear()
        self.combo_isotope.addItems(isotopes)
        self.combo_isotope.blockSignals(False)

    def contextMenuEvent(self, event: QtCore.QEvent) -> None:
        context_menu = self.buildContextMenu()
        context_menu.exec(event.globalPos())

    def onMenuCopy(self) -> None:
        laser_copy = copy.deepcopy(self.laser)
        dock_copy = type(self)(laser_copy, self.parent())
        self.parent().smartSplitDock(self, dock_copy)

    def onMenuSave(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save File", "", "Numpy archive(*.npz);;All files(*)"
        )
        if path:
            io.npz.save(path, [self.laser])

    def onMenuExport(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export",
            "",
            "CSV files(*.csv);;Numpy archives(*.npz);;"
            "PNG images(*.png);;VTK Images(*.vti);;All files(*)",
            options=QtWidgets.QFileDialog.DontConfirmOverwrite,
        )
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()

        if ext in [".npz", ".vti"]:  # Show an overwrite dialog
            if not OverwriteFilePrompt.promptOverwriteSingleFile(path, self):
                return self.onMenuExport()

        if ext == ".csv":
            dlg: ExportDialog = CSVExportDialog(
                path,
                name=self.combo_isotope.currentText(),
                names=len(self.laser.isotopes()),
                layers=1,
                parent=self,
            )
            if dlg.exec():
                paths = dlg.generate_paths(self.laser)
                extent = None
                if dlg.options.trimmedChecked():
                    extent = self.canvas.view
                for path, isotope, _ in paths:
                    io.csv.save(
                        path,
                        self.laser,
                        isotope,
                        extent=extent,
                        include_header=dlg.options.headerChecked(),
                    )

        elif ext == ".npz":
            io.npz.save(path, [self.laser])
        elif ext == ".png":
            dlg = PNGExportDialog(
                path,
                name=self.combo_isotope.currentText(),
                names=len(self.laser.isotopes()),
                layers=1,
                parent=self,
            )
            if dlg.exec():
                paths = dlg.generate_paths(self.laser)
                for path, isotope, _ in paths:
                    io.png.save(
                        path,
                        self.laser,
                        isotope,
                        extent=self.canvas.view,
                        viewconfig=self.window().viewconfig,
                        size=dlg.options.imagesize(),
                        include_colorbar=dlg.options.colorbarChecked(),
                        include_scalebar=dlg.options.scalebarChecked(),
                        include_label=dlg.options.labelChecked(),
                    )
        elif ext == ".vti":
            io.vtk.save(path, self.laser)
        else:
            QtWidgets.QMessageBox.warning(
                self, "Invalid Format", f"Unable to export {ext} format."
            )
            return self.onMenuExport()

    def onMenuCalibration(self) -> None:
        def applyDialog(dialog: ApplyDialog) -> None:
            if dialog.check_all.isChecked():
                docks = self.parent().findChildren(LaserImageDock)
            else:
                docks = [self]
            for dock in docks:
                for isotope in dlg.calibration.keys():
                    if isotope in dock.laser.isotopes():
                        dock.laser.data[isotope].gradient = dlg.calibration[isotope][0]
                        dock.laser.data[isotope].isotope = dlg.calibration[isotope][1]
                        dock.laser.data[isotope].unit = dlg.calibration[isotope][2]
                dock.draw()

        dlg = CalibrationDialog(
            self.laser, self.combo_isotope.currentText(), parent=self
        )
        dlg.applyPressed.connect(applyDialog)
        if dlg.exec():
            applyDialog(dlg)

    def onMenuConfig(self) -> None:
        def applyDialog(dialog: ApplyDialog) -> None:
            if dialog.check_all.isChecked():
                docks = self.parent().findChildren(LaserImageDock)
            else:
                docks = [self]
            for dock in docks:
                if type(dock.laser) == Laser:
                    dock.laser.config = copy.copy(dialog.config)
                    dock.draw()

        dlg = ConfigDialog(self.laser.config, parent=self)
        dlg.applyPressed.connect(applyDialog)
        if dlg.exec():
            applyDialog(dlg)

    def onMenuStats(self) -> None:
        return
        dlg = StatsDialog(self.laser, self.window().viewconfig, parent=self)
        dlg.exec()

    # def onMenuCalculate(self) -> None:
    #     def applyDialog(dialog: ApplyDialog) -> None:
    #         if dialog.data is None or hasattr(self.laser.data, dialog.data.name):
    #             return
    #         self.laser.data[dialog.data.name] = dialog.data
    #         self.populateComboIsotopes()

    #     dlg = CalculateDialog(self.laser, parent=self)
    #     dlg.applyPressed.connect(applyDialog)
    #     if dlg.exec():
    #         applyDialog(dlg)

    def onMenuClose(self) -> None:
        self.close()

    def onComboIsotope(self, text: str) -> None:
        self.draw()

    def titleNameChanged(self, name: str) -> None:
        self.setWindowTitle(name)
        if self.laser is not None:
            self.laser.name = name
