from PySide6 import QtCore


class DragDropRedirectFilter(QtCore.QObject):  # pragma: no cover
    """Redirects drag and drop events to parent."""

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.DragEnter:
            self.parent().dragEnterEvent(event)
            return True
        elif event.type() == QtCore.QEvent.DragLeave:
            self.parent().dragLeaveEvent(event)
            return True
        elif event.type() == QtCore.QEvent.DragMove:
            self.parent().dragMoveEvent(event)
            return True
        elif event.type() == QtCore.QEvent.Drop:
            self.parent().dropEvent(event)
            return True
        return bool(super().eventFilter(obj, event))


class MousePressRedirectFilter(QtCore.QObject):
    """Redirects mouse press events to parent."""

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.parent().mousePressEvent(event)
            return False
        return bool(super().eventFilter(obj, event))
