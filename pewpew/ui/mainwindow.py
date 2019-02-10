import os.path
import sys
import traceback

from PyQt5 import QtCore, QtGui, QtWidgets

from pewpew import __version__
from pewpew.ui.dialogs import (
    ConfigDialog,
    ColorRangeDialog,
    FilteringDialog,
    TrimDialog,
)
from pewpew.ui.docks import ImageDock, LaserImageDock, KrissKrossImageDock
from pewpew.ui.tools import CalibrationTool
from pewpew.ui.widgets.overwritefileprompt import OverwriteFilePrompt
from pewpew.ui.widgets.detailederror import DetailedError
from pewpew.ui.widgets.multipledirdialog import MultipleDirDialog
from pewpew.ui.docks.dockarea import DockArea
from pewpew.ui.wizards import KrissKrossWizard
from pewpew.ui.dialogs.export import ExportAllDialog

from pewpew.lib.colormaps import COLORMAPS
from pewpew.lib.exceptions import PewPewError, PewPewFileError
from pewpew.lib import io
from pewpew.lib.krisskross import KrissKrossData
from pewpew.lib.laser import LaserData

from typing import List
from types import TracebackType
from pewpew.ui.dialogs import ApplyDialog


## TODO replace trim parameter with axis limits, easier
## TODO phil would like to have a way to average an area, without background
## TODO imagedock is useless, make it just laserimagedock


class MainWindow(QtWidgets.QMainWindow):
    INTERPOLATIONS = ["None", "Bilinear", "Bicubic", "Gaussian", "Spline16"]
    FILTERS = ["None", "Rolling mean", "Rolling median"]
    DEFAULT_VIEW_CONFIG = {
        "cmap": {"type": "ppSpectral", "range": ("2%", "98%")},
        "filtering": {"type": "None", "window": (5, 5), "threshold": 5},
        "interpolation": "None",
        "font": {"size": 12},
    }

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        # Defaults for when applying to multiple images
        self.config: dict = LaserData.DEFAULT_CONFIG
        self.viewconfig: dict = MainWindow.DEFAULT_VIEW_CONFIG
        self.setWindowTitle("Pew Pew")
        self.resize(1280, 800)

        widget = QtWidgets.QWidget()
        self.setCentralWidget(widget)
        layout = QtWidgets.QHBoxLayout()

        self.dockarea = DockArea(self)
        layout.addWidget(self.dockarea)

        widget.setLayout(layout)

        self.createMenus()
        self.statusBar().showMessage("Import or open data to begin.")

    def createMenus(self) -> None:
        # File
        menu_file = self.menuBar().addMenu("&File")
        action_open = menu_file.addAction(
            QtGui.QIcon.fromTheme("document-open"), "&Open"
        )
        action_open.setShortcut("Ctrl+O")
        action_open.setStatusTip("Open sessions and images.")
        action_open.triggered.connect(self.menuOpen)

        # File -> Import
        menu_import = menu_file.addMenu("&Import")
        action_import = menu_import.addAction("&Agilent Batch")
        action_import.setStatusTip("Import Agilent image data (.b).")
        action_import.triggered.connect(self.menuImportAgilent)

        action_import = menu_import.addAction("&Thermo iCap CSV")
        action_import.setStatusTip(
            "Import data exported using the CSV export function."
        )
        action_import.triggered.connect(self.menuImportThermoiCap)

        action_import = menu_import.addAction("&Kriss Kross...")
        action_import.setStatusTip("Start the Kriss Kross import wizard.")
        action_import.triggered.connect(self.menuImportKrissKross)

        menu_file.addSeparator()

        action_save = menu_file.addAction(
            QtGui.QIcon.fromTheme("document-save"), "&Save Session"
        )
        action_save.setShortcut("Ctrl+S")
        action_save.setStatusTip("Save session to file.")
        action_save.triggered.connect(self.menuSaveSession)
        action_save.setEnabled(False)

        action_export = menu_file.addAction(
            QtGui.QIcon.fromTheme("document-save-as"), "&Export all"
        )
        action_export.setShortcut("Ctrl+X")
        action_export.setStatusTip("Export all images to a different format.")
        action_export.triggered.connect(self.menuExportAll)

        menu_file.addSeparator()

        action_close = menu_file.addAction(
            QtGui.QIcon.fromTheme("edit-delete"), "Close All"
        )
        action_close.setStatusTip("Close all open images.")
        action_close.setShortcut("Ctrl+Q")
        action_close.triggered.connect(self.menuCloseAll)

        menu_file.addSeparator()

        action_exit = menu_file.addAction(
            QtGui.QIcon.fromTheme("application-exit"), "E&xit"
        )
        action_exit.setStatusTip("Quit the program.")
        action_exit.setShortcut("Ctrl+Shift+Q")
        action_exit.triggered.connect(self.menuExit)

        # Edit
        menu_edit = self.menuBar().addMenu("&Edit")
        action_config = menu_edit.addAction(
            QtGui.QIcon.fromTheme("document-properties"), "&Config"
        )
        action_config.setStatusTip("Update the configs for visible images.")
        action_config.setShortcut("Ctrl+K")
        action_config.triggered.connect(self.menuConfig)

        action_trim = menu_edit.addAction(QtGui.QIcon.fromTheme("edit-cut"), "&Trim")
        action_trim.setStatusTip("Update trim for visible images.")
        action_trim.setShortcut("Ctrl+T")
        action_trim.triggered.connect(self.menuTrim)

        menu_edit.addSeparator()

        action_calibration = menu_edit.addAction(
            QtGui.QIcon.fromTheme(""), "&Standards"
        )
        action_calibration.setStatusTip("Generate calibration curve from a standard.")
        action_calibration.triggered.connect(self.menuStandardsTool)

        # View
        menu_view = self.menuBar().addMenu("&View")
        menu_cmap = menu_view.addMenu("&Colormap")
        menu_cmap.setStatusTip("Colormap of displayed images.")

        # View - colormap
        cmap_group = QtWidgets.QActionGroup(menu_cmap)
        for name, cmap, print_safe, cb_safe, description in COLORMAPS:
            action = cmap_group.addAction(name)
            if print_safe:
                description += " Print safe."
            if cb_safe:
                description += " Colorblind safe."
            action.setStatusTip(description)
            action.setCheckable(True)
            if cmap == self.viewconfig["cmap"]["type"]:
                action.setChecked(True)
            menu_cmap.addAction(action)
        cmap_group.triggered.connect(self.menuColormap)
        menu_cmap.addSeparator()
        action_cmap_range = menu_cmap.addAction("&Range...")
        action_cmap_range.setStatusTip(
            "Set the minimum and maximum values or percentiles of the colormap."
        )
        action_cmap_range.setShortcut("Ctrl+R")
        action_cmap_range.triggered.connect(self.menuColormapRange)

        # View - interpolation
        menu_interp = menu_view.addMenu("&Interpolation")
        menu_interp.setStatusTip("Interpolation of displayed images.")
        interp_group = QtWidgets.QActionGroup(menu_interp)
        for interp in MainWindow.INTERPOLATIONS:
            action = interp_group.addAction(interp)
            action.setCheckable(True)
            if interp == self.viewconfig["interpolation"]:
                action.setChecked(True)
            menu_interp.addAction(action)
        interp_group.triggered.connect(self.menuInterpolation)

        # View - filtering
        menu_filter = menu_view.addMenu("&Filtering")
        menu_filter.setStatusTip("Apply filtering to images.")
        filter_group = QtWidgets.QActionGroup(menu_filter)
        for filter in MainWindow.FILTERS:
            action = filter_group.addAction(filter)
            action.setCheckable(True)
            if filter == self.viewconfig["filtering"]["type"]:
                action.setChecked(True)
            menu_filter.addAction(action)
        filter_group.triggered.connect(self.menuFiltering)

        action_filter_properties = menu_filter.addAction("Properties...")
        action_filter_properties.setStatusTip("Set the properties used by filters.")
        action_filter_properties.triggered.connect(self.menuFilteringProperties)

        action_fontsize = menu_view.addAction("Fontsize")
        action_fontsize.setStatusTip("Set size of font used in images.")
        action_fontsize.triggered.connect(self.menuFontsize)

        menu_view.addSeparator()

        action_refresh = menu_view.addAction(
            QtGui.QIcon.fromTheme("view-refresh"), "Refresh"
        )
        action_refresh.setStatusTip("Redraw all images.")
        action_refresh.setShortcut("F5")
        action_refresh.triggered.connect(self.menuRefresh)

        # Help
        menu_help = self.menuBar().addMenu("&Help")
        action_about = menu_help.addAction(
            QtGui.QIcon.fromTheme("help-about"), "&About"
        )
        action_about.setStatusTip("About this program.")
        action_about.triggered.connect(self.menuAbout)

    def refresh(self, visible_only: bool = False) -> None:
        if visible_only:
            docks = self.dockarea.visibleDocks()
        else:
            docks = self.dockarea.findChildren(ImageDock)
        for d in docks:
            d.draw()

    def menuOpen(self) -> None:
        paths, _filter = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open File(s).",
            "",
            "CSV files(*.csv);;Numpy Archives(*.npz);;"
            "Pew Pew Sessions(*.pew);;All files(*)",
            "All files(*)",
        )
        lds: List[LaserData] = []
        if len(paths) == 0:
            return
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".npz":
                    lds += io.npz.load(path)
                elif ext == ".csv":
                    lds.append(io.csv.load(path))
                else:
                    raise PewPewFileError("Invalid file extension.")
            except PewPewError as e:
                QtWidgets.QMessageBox.warning(
                    self, type(e).__name__, f"{os.path.basename(path)}: {e}"
                )
                return
        docks = []
        for ld in lds:
            if isinstance(ld, KrissKrossData):
                docks.append(KrissKrossImageDock(ld, self.dockarea))
            else:
                docks.append(LaserImageDock(ld, self.dockarea))
        self.dockarea.addDockWidgets(docks)

    def menuImportAgilent(self) -> None:
        paths = MultipleDirDialog.getExistingDirectories("Batch Directories", "", self)
        if len(paths) == 0:
            return
        docks = []
        for path in paths:
            try:
                if path.lower().endswith(".b"):
                    ld = io.agilent.load(path, config=self.config)
                    docks.append(LaserImageDock(ld, self.dockarea))
                else:
                    raise PewPewFileError("Invalid batch directory.")
            except PewPewError as e:
                QtWidgets.QMessageBox.warning(
                    self, type(e).__name__, f"{os.path.basename(path)}: {e}"
                )
                return
        self.dockarea.addDockWidgets(docks)

    def menuImportThermoiCap(self) -> None:
        paths, _filter = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Import CSVs", "", "CSV files(*.csv);;All files(*)"
        )

        if len(paths) == 0:
            return
        docks = []
        for path in paths:
            try:
                if path.lower().endswith(".csv"):
                    ld = io.thermo.load(path, config=self.config)
                    docks.append(LaserImageDock(ld, self.dockarea))
                else:
                    raise PewPewFileError("Invalid file.")
            except PewPewError as e:
                QtWidgets.QMessageBox.warning(
                    self, type(e).__name__, f"{os.path.basename(path)}: {e}"
                )
                return
        self.dockarea.addDockWidgets(docks)

    def menuImportKrissKross(self) -> None:
        kkw = KrissKrossWizard(self.config, parent=self)
        if kkw.exec():
            dock = KrissKrossImageDock(kkw.data, self.dockarea)
            self.dockarea.addDockWidgets([dock])

    def menuSaveSession(self) -> None:
        # Save the window state
        settings = QtCore.QSettings("Pewpew", "Pewpew")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        print(settings.allKeys())
        print(settings)

        docks = self.dockarea.findChildren(ImageDock)
        if len(docks) == 0:
            QtWidgets.QMessageBox.information(self, "Save Session", "Nothing to save.")
            return
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save File", "", "Pew Pew sessions(*.pew);;All files(*)"
        )
        if path == "":
            return
        lds = [d.laser for d in docks]
        io.npz.save(path, lds)

    def menuExportAll(self) -> None:
        lasers = [dock.laser for dock in self.dockarea.findChildren(ImageDock)]
        if len(lasers) == 0:
            return

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Export To Directory", ""
        )
        if not path:
            return

        isotopes = list(set.union(*[set(laser.isotopes()) for laser in lasers]))
        dlg = ExportAllDialog(path, lasers[0].name, isotopes, 1, self)
        if not dlg.exec():
            return

        prompt = OverwriteFilePrompt(parent=self)
        for laser in lasers:
            paths = dlg.generate_paths(laser, prompt=prompt)
            ext = ExportAllDialog.FORMATS[dlg.combo_formats.currentText()]

            for path, isotope, _ in paths:
                if ext == ".csv":
                    io.csv.save(
                        path,
                        laser,
                        isotope,
                        trimmed=dlg.options.csv.hasTrimmed(),
                        include_header=dlg.options.csv.hasHeader(),
                    )
                elif ext == ".npz":
                    io.npz.save(path, [laser])
                elif ext == ".png":
                    io.png.save(
                        path,
                        laser,
                        isotope,
                        self.viewconfig,
                        size=dlg.options.png.imagesize(),
                        include_colorbar=dlg.options.png.hasColorbar(),
                        include_scalebar=dlg.options.png.hasScalebar(),
                        include_label=dlg.options.png.hasLabel(),
                    )
                elif ext == ".vti":
                    io.npz.save(path, laser)
                else:
                    QtWidgets.QMessageBox.warning(
                        self, "Invalid Format", f"Unable to export {ext} format."
                    )
                    return

    def menuCloseAll(self) -> None:
        for dock in self.dockarea.findChildren(ImageDock):
            dock.close()

    def menuExit(self) -> None:
        self.close()

    def menuConfig(self) -> None:
        def applyDialog(dialog: ApplyDialog) -> None:
            self.config["spotsize"] = dialog.spotsize
            self.config["speed"] = dlg.speed
            self.config["scantime"] = dlg.scantime
            for dock in self.dockarea.findChildren(LaserImageDock):
                dock.laser.config["spotsize"] = dlg.spotsize
                dock.laser.config["speed"] = dlg.speed
                dock.laser.config["scantime"] = dlg.scantime
                dock.draw()

        dlg = ConfigDialog(self.config, parent=self)
        dlg.applyPressed.connect(applyDialog)
        dlg.check_all.setEnabled(False)
        dlg.check_all.setChecked(True)

        if dlg.exec():
            applyDialog(dlg)

    def menuTrim(self) -> None:
        def applyDialog(dialog: ApplyDialog) -> None:
            # Ensure that trim isn't too large
            for dock in self.dockarea.findChildren(LaserImageDock):
                total = sum(
                    dock.laser.convertTrim(dialog.trim, dialog.combo_trim.currentText())
                )
                if total > dock.laser.data.shape[1]:
                    QtWidgets.QMessageBox.warning(
                        self, "Invalid Trim", "Trim larger than data."
                    )
                    return
            for dock in self.dockarea.findChildren(LaserImageDock):
                dock.laser.setTrim(dialog.trim, dialog.combo_trim.currentText())
                dock.draw()

        dlg = TrimDialog((0.0, 0.0), parent=self)
        dlg.applyPressed.connect(applyDialog)
        dlg.check_all.setEnabled(False)
        dlg.check_all.setChecked(True)

        if dlg.exec():
            applyDialog(dlg)

    def menuStandardsTool(self) -> None:
        def applyDialog(dialog: ApplyDialog) -> None:
            for dock in self.dockarea.findChildren(LaserImageDock):
                for isotope in dlg.calibration.keys():
                    if isotope in dock.laser.calibration.keys():
                        dock.laser.calibration[isotope] = dict(dlg.calibration[isotope])
                dock.draw()

        docks = self.dockarea.orderedDocks(self.dockarea.visibleDocks(LaserImageDock))
        laser = docks[0] if len(docks) > 0 else LaserImageDock(LaserData(), parent=self)
        dlg = CalibrationTool(laser, self.dockarea, self.viewconfig, parent=self)
        dlg.applyPressed.connect(applyDialog)
        dlg.show()

    def menuColormap(self, action: QtWidgets.QAction) -> None:
        text = action.text().replace("&", "")
        for name, cmap, _, _, _ in COLORMAPS:
            if name == text:
                self.viewconfig["cmap"]["type"] = cmap
                self.refresh()
                return

    def menuColormapRange(self) -> None:
        def applyDialog(dialog: ApplyDialog) -> None:
            self.viewconfig["cmap"]["range"] = dialog.range
            self.refresh()

        dlg = ColorRangeDialog(self.viewconfig["cmap"]["range"], parent=self)
        dlg.applyPressed.connect(applyDialog)
        if dlg.exec():
            applyDialog(dlg)

    def menuInterpolation(self, action: QtWidgets.QAction) -> None:
        self.viewconfig["interpolation"] = action.text().replace("&", "")
        self.refresh()

    def menuFiltering(self, action: QtWidgets.QAction) -> None:
        self.viewconfig["filtering"]["type"] = action.text().replace("&", "")
        self.refresh()

    def menuFilteringProperties(self) -> None:
        def applyDialog(dialog: ApplyDialog) -> None:
            self.viewconfig["filtering"]["window"] = dialog.window
            self.viewconfig["filtering"]["threshold"] = dialog.threshold
            self.refresh()

        dlg = FilteringDialog(
            self.viewconfig["filtering"]["window"],
            self.viewconfig["filtering"]["threshold"],
            parent=self,
        )
        dlg.applyPressed.connect(applyDialog)
        if dlg.exec():
            applyDialog(dlg)

    def menuFontsize(self) -> None:
        fontsize, ok = QtWidgets.QInputDialog.getInt(
            self,
            "Fontsize",
            "Fontsize",
            value=self.viewconfig["font"]["size"],
            min=0,
            max=100,
            step=1,
        )
        if ok:
            self.viewconfig["font"]["size"] = fontsize
            self.refresh()

    def menuRefresh(self) -> None:
        self.refresh()

    def menuAbout(self) -> None:
        QtWidgets.QMessageBox.about(
            self,
            "About Laser plot",
            (
                "Visualiser / converter for LA-ICP-MS data.\n"
                f"Version {__version__}\n"
                "Developed by the UTS Elemental Bio-Imaging Group.\n"
                "https://github.com/djdt/pewpew"
            ),
        )

    def exceptHook(self, type: type, value: BaseException, tb: TracebackType) -> None:
        if type == KeyboardInterrupt:
            print("Keyboard interrupt, exiting.")
            sys.exit(1)
        DetailedError.critical(
            type.__name__,
            str(value),
            "".join(traceback.format_exception(type, value, tb)),
            self,
        )

    def closeEvent(self, event: QtCore.QEvent) -> None:
        for dock in self.dockarea.findChildren(ImageDock):
            dock.close()
        super().closeEvent(event)