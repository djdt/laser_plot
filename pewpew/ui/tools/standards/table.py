from PyQt5 import QtCore, QtWidgets

from pewpew.ui.widgets.basictable import BasicTable
from pewpew.ui.validators import DoublePrecisionDelegate


class StandardsTable(BasicTable):
    ROW_LABELS = [c for c in "ABCDEFGHIJKLMNOPQRST"]
    COLUMN_CONC = 0
    COLUMN_COUNT = 1

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["Concentration", "Counts"])
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setItemDelegate(DoublePrecisionDelegate(4))

    def isComplete(self) -> bool:
        for row in range(0, self.rowCount()):
            for column in range(0, self.columnCount()):
                if self.item(row, column).text() == "":
                    return False
        return True

    def setRowCount(self, rows: int) -> None:
        current_rows = self.rowCount()
        super().setRowCount(rows)

        if current_rows < rows:
            self.setVerticalHeaderLabels(StandardsTable.ROW_LABELS)
            for row in range(current_rows, rows):
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.setItem(row, 0, item)
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                # Non editable item
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.setItem(row, 1, item)