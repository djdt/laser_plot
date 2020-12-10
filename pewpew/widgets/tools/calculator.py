import numpy as np
import logging

from PySide2 import QtCore, QtGui, QtWidgets

from pewlib.process import convolve, filters
from pewlib.process.calc import normalise
from pewlib.process.threshold import otsu

from pewpew.actions import qAction, qToolButton
from pewpew.lib import kmeans
from pewpew.lib.pratt import Parser, ParserException, Reducer, ReducerException
from pewpew.lib.pratt import BinaryFunction, UnaryFunction, TernaryFunction

from pewpew.widgets.canvases import BasicCanvas, LaserImageCanvas
from pewpew.widgets.ext import ValidColorLineEdit, ValidColorTextEdit
from pewpew.widgets.laser import LaserWidget
from pewpew.widgets.tools import ToolWidget

from pewpew.validators import DecimalValidator, LimitValidator, OddIntValidator

from typing import List, Tuple


# TODO
# Add some kind of indicator for if all data or just current isotope changed

logger = logging.getLogger(__name__)


class CalculatorName(ValidColorLineEdit):
    def __init__(
        self,
        text: str,
        badnames: List[str],
        badparser: List[str],
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(text, parent)

        self.badnames = badnames
        self.badchars = [" ", "\t", "\n"]
        self.badnulls = ["nan", "if", "then", "else"]
        self.badnulls.extend(badparser)

    def hasAcceptableInput(self) -> bool:
        if self.text() == "":
            return False
        if any(char in self.text() for char in self.badchars):
            return False
        if self.text() in self.badnulls:
            return False
        if self.text() in self.badnames:
            return False
        return True


class CalculatorFormula(ValidColorTextEdit):
    def __init__(
        self, text: str, variables: List[str], parent: QtWidgets.QWidget = None
    ):
        super().__init__(text, parent)
        self.textChanged.disconnect(self.revalidate)
        self.textChanged.connect(self.calculate)
        self.parser = Parser(variables)
        self.expr = ""

    def hasAcceptableInput(self) -> bool:
        return self.expr != ""

    def calculate(self) -> None:
        try:
            self.expr = self.parser.parse(self.toPlainText())
        except ParserException:
            self.expr = ""
        self.revalidate()


class CalculatorTool(ToolWidget):
    parser_functions = {
        "abs": (UnaryFunction("abs"), "(<x>)", "The absolute value of <x>."),
        "kmeans": (
            BinaryFunction("kmeans"),
            "(<x>, <k>)",
            "Returns lower bounds of 1 to <k> kmeans clusters.",
        ),
        "mean": (UnaryFunction("mean"), "(<x>)", "Returns the mean of <x>."),
        "median": (
            UnaryFunction("median"),
            "(<x>)",
            "Returns the median of <x>.",
        ),
        "nantonum": (UnaryFunction("nantonum"), "(<x>)", "Sets nan values to 0."),
        "normalise": (
            TernaryFunction("normalise"),
            "(<x>, <min>, <max>)",
            "Normalise <x> from from <min> to <max>.",
        ),
        "otsu": (
            UnaryFunction("otsu"),
            "(<x>)",
            "Returns Otsu's threshold for <x>.",
        ),
        "percentile": (
            BinaryFunction("percentile"),
            "(<x>, <percent>)",
            "Returns the <percent> percentile of <x>.",
        ),
        "threshold": (
            BinaryFunction("threshold"),
            "(<x>, <value>)",
            "Sets <x> below <value> to NaN.",
        ),
    }
    reducer_functions = {
        "abs": (np.abs, 1),
        "kmeans": (kmeans.thresholds, 2),
        "mean": (np.nanmean, 1),
        "median": (np.nanmedian, 1),
        "nantonum": (np.nan_to_num, 1),
        "normalise": (normalise, 3),
        "otsu": (otsu, 1),
        "percentile": (np.nanpercentile, 2),
        "threshold": (lambda x, a: np.where(x > a, x, np.nan), 2),
    }

    def __init__(self, widget: LaserWidget):
        super().__init__(widget, canvas_label="Preview")

        self.canvas = LaserImageCanvas(
            self.viewspace.options, move_button=1, parent=self
        )
        self.canvas.drawFigure()
        self.canvas.cursorClear.connect(self.widget.clearCursorStatus)
        self.canvas.cursorMoved.connect(self.widget.updateCursorStatus)
        self.canvas.view_limits = self.widget.canvas.view_limits


        self.output = QtWidgets.QLineEdit("Result")
        self.output.setEnabled(False)

        self.lineedit_name = CalculatorName(
            "",
            badnames=[],
            badparser=list(CalculatorTool.parser_functions.keys()),
        )
        self.lineedit_name.revalidate()
        self.lineedit_name.textEdited.connect(self.completeChanged)
        self.lineedit_name.textEdited.connect(self.refresh)

        self.combo_isotope = QtWidgets.QComboBox()
        self.combo_isotope.activated.connect(self.insertVariable)

        functions = [k + v[1] for k, v in CalculatorTool.parser_functions.items()]
        tooltips = [v[2] for v in CalculatorTool.parser_functions.values()]
        self.combo_function = QtWidgets.QComboBox()
        self.combo_function.addItem("Functions")
        self.combo_function.addItems(functions)
        for i in range(0, len(tooltips)):
            self.combo_function.setItemData(i + 1, tooltips[i], QtCore.Qt.ToolTipRole)
        self.combo_function.activated.connect(self.insertFunction)

        self.reducer = Reducer({})
        self.formula = CalculatorFormula("", variables=[])
        self.formula.textChanged.connect(self.completeChanged)
        self.formula.textChanged.connect(self.refresh)

        self.reducer.operations.update(CalculatorTool.reducer_functions)
        self.formula.parser.nulls.update(
            {k: v[0] for k, v in CalculatorTool.parser_functions.items()}
        )

        layout_combos = QtWidgets.QHBoxLayout()
        layout_combos.addWidget(self.combo_isotope)
        layout_combos.addWidget(self.combo_function)

        layout_canvas = QtWidgets.QVBoxLayout()
        layout_canvas.addWidget(self.canvas)
        self.box_canvas.setLayout(layout_canvas)

        layout_controls = QtWidgets.QFormLayout()
        layout_controls.addRow("Name:", self.lineedit_name)
        layout_controls.addRow("Insert:", layout_combos)
        layout_controls.addRow("Formula:", self.formula)
        layout_controls.addRow("Result:", self.output)
        self.box_controls.setLayout(layout_controls)

        self.initialise()

    def apply(self) -> None:
        name = self.lineedit_name.text()
        data = self.reducer.reduce(self.formula.expr)
        if name in self.widget.laser.isotopes:
            self.widget.laser.data[name] = data
        else:
            self.widget.laser.add(self.lineedit_name.text(), data)
        # Make sure to repop isotopes
        self.widget.populateIsotopes()

    def initialise(self) -> None:
        isotopes = self.widget.laser.isotopes
        self.combo_isotope.clear()
        self.combo_isotope.addItem("Isotopes")
        self.combo_isotope.addItems(isotopes)

        name = "calc0"
        i = 1
        while name in isotopes:
            name = f"calc{i}"
            i += 1
        self.lineedit_name.setText(name)
        self.formula.parser.variables = isotopes
        self.formula.valid = True
        self.formula.setText(self.widget.combo_isotope.currentText())

    def insertFunction(self, index: int) -> None:
        if index == 0:
            return
        function = self.combo_function.itemText(index)
        function = function[: function.find("(") + 1]
        self.formula.insertPlainText(function)
        self.combo_function.setCurrentIndex(0)
        self.formula.setFocus()

    def insertVariable(self, index: int) -> None:
        if index == 0:
            return
        self.formula.insertPlainText(self.combo_isotope.itemText(index))
        self.combo_isotope.setCurrentIndex(0)
        self.formula.setFocus()

    def isComplete(self) -> bool:
        if not self.formula.hasAcceptableInput():
            return False
        if not self.lineedit_name.hasAcceptableInput():
            return False
        return True

    def previewData(self, data: np.ndarray) -> np.ndarray:
        self.reducer.variables = {name: data[name] for name in data.dtype.names}
        try:
            data = self.reducer.reduce(self.formula.expr)
            if np.isscalar(data):
                self.output.setText(f"{data:.10g}")
                return None
            elif isinstance(data, np.ndarray) and data.ndim == 1:
                self.output.setText(f"{list(map('{:.4g}'.format, data))}")
                return None
            elif isinstance(data, np.ndarray):
                self.output.setText(f"{data.dtype.name} array: {data.shape}")
                return data
        except (ReducerException, ValueError) as e:
            self.output.setText(str(e))
            return None


    def refresh(self) -> None:
        if not self.isComplete():  # Not ready for update to preview
            return

        isotope = self.combo_isotope.currentText()

        data = self.previewData(self.widget.laser.get(flat=True, calibrated=False))
        if data is None:
            return
        extent = self.widget.laser.config.data_extent(data.shape)

        # Only change the view if new or the laser extent has changed (i.e. conf edit)
        if self.canvas.extent != extent:
            self.canvas.view_limits = self.canvas.extentForAspect(extent)

        self.canvas.drawData(
            data,
            extent,
            isotope=isotope,
        )

        if self.canvas.viewoptions.canvas.colorbar:
            self.canvas.drawColorbar("")

        if self.canvas.viewoptions.canvas.label:
            self.canvas.drawLabel(self.lineedit_name.text())
        elif self.canvas.label is not None:
            self.canvas.label.remove()
            self.canvas.label = None

        if self.canvas.viewoptions.canvas.scalebar:
            self.canvas.drawScalebar()
        elif self.canvas.scalebar is not None:
            self.canvas.scalebar.remove()
            self.canvas.scalebar = None

        self.canvas.draw_idle()
