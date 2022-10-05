from pytestqt.qtbot import QtBot

from PySide6 import QtCore, QtWidgets

from pewpew.widgets.views import ViewSpace, View, _ViewWidget


# Most of the drag/drop actions are not tested and have no cover.


class _TestViewWidget(_ViewWidget):
    def __init__(self, idx: int, view: View, editable: bool = False):
        self.idx = idx
        super().__init__(view, editable)

    def rename(self, text: str) -> None:
        pass


def test_view_space_active(qtbot: QtBot):
    viewspace = ViewSpace()
    qtbot.addWidget(viewspace)
    viewspace.show()
    # Default active
    assert viewspace.activeView() == viewspace.views[0]
    # Focus new widget
    viewspace.splitActiveHorizontal()
    assert viewspace.activeView() == viewspace.views[1]
    # Test stack changes active
    qtbot.mouseClick(viewspace.views[0].stack, QtCore.Qt.LeftButton)
    assert viewspace.activeView() == viewspace.views[0]
    # Test focus on tab changes active
    qtbot.mouseClick(viewspace.views[1].tabs, QtCore.Qt.LeftButton)
    assert viewspace.activeView() == viewspace.views[1]


def test_view_space_add_remove(qtbot: QtBot):
    viewspace = ViewSpace()
    qtbot.addWidget(viewspace)
    viewspace.show()

    assert len(viewspace.views) == 1

    with qtbot.waitSignal(viewspace.numViewsChanged):
        viewspace.splitActiveHorizontal()
    assert len(viewspace.views) == 2

    viewspace.setActiveView(viewspace.views[1])
    with qtbot.waitSignal(viewspace.numViewsChanged):
        viewspace.splitActiveVertical()
    assert len(viewspace.views) == 3

    with qtbot.waitSignal(viewspace.numViewsChanged):
        viewspace.splitView(viewspace.views[2], QtCore.Qt.Horizontal)
    assert len(viewspace.views) == 4

    # Should be 1 view on left, 1 on top right, 2 bottom right
    assert viewspace.count() == 2
    assert isinstance(viewspace.widget(0), View)
    assert isinstance(viewspace.widget(1), QtWidgets.QSplitter)

    assert viewspace.widget(1).count() == 2
    assert isinstance(viewspace.widget(1).widget(0), View)
    assert isinstance(viewspace.widget(1).widget(1), QtWidgets.QSplitter)

    assert viewspace.widget(1).widget(1).count() == 2
    assert isinstance(viewspace.widget(1).widget(1).widget(0), View)
    assert isinstance(viewspace.widget(1).widget(1).widget(1), View)

    with qtbot.waitSignal(viewspace.numViewsChanged):
        viewspace.closeView(viewspace.views[0])
    assert len(viewspace.views) == 3

    # Should be 1 view on top, 1 on bottom left, 1 bottom right
    # Original splitter changes orientation, inherits children of right splitter
    assert viewspace.count() == 2
    assert viewspace.orientation() == QtCore.Qt.Vertical
    assert isinstance(viewspace.widget(0), View)
    assert isinstance(viewspace.widget(1), QtWidgets.QSplitter)

    assert viewspace.widget(1).count() == 2
    assert isinstance(viewspace.widget(1).widget(0), View)
    assert isinstance(viewspace.widget(1).widget(1), View)

    # Active widget should be first in latest view
    for view in viewspace.views:
        view.addTab("", _ViewWidget(view))

    assert viewspace.activeWidget() == viewspace.views[2].widgets()[0]
    assert viewspace.countViewTabs() == 3

    # Close them all
    with qtbot.waitSignal(viewspace.numViewsChanged):
        viewspace.closeActiveView()
    assert len(viewspace.views) == 2
    with qtbot.waitSignal(viewspace.numViewsChanged):
        viewspace.closeActiveView()
    assert len(viewspace.views) == 1
    with qtbot.assertNotEmitted(viewspace.numViewsChanged, wait=100):
        viewspace.closeActiveView()
    assert len(viewspace.views) == 1

    assert viewspace.countViewTabs() == 1


def test_view_tabs(qtbot: QtBot):
    viewspace = ViewSpace()
    qtbot.addWidget(viewspace)
    viewspace.show()
    view = viewspace.activeView()
    # Creating tabs
    with qtbot.waitSignal(view.numTabsChanged):
        view.addTab("1", _TestViewWidget(1, view))
    with qtbot.waitSignal(viewspace.numTabsChanged):
        view.addTab("3", _TestViewWidget(3, view))
    with qtbot.waitSignal(view.numTabsChanged):
        view.insertTab(1, "2", _TestViewWidget(2, view))
    assert view.tabs.count() == 3
    assert [view.tabs.tabText(i) for i in range(3)] == ["1", "2", "3"]
    assert [view.stack.widget(i).idx for i in range(3)] == [1, 2, 3]
    # Moving tabs
    with qtbot.assertNotEmitted(view.numTabsChanged, wait=100):
        view.tabs.moveTab(2, 0)
    assert [view.tabs.tabText(i) for i in range(3)] == ["3", "1", "2"]
    assert [view.stack.widget(i).idx for i in range(3)] == [3, 1, 2]
    # Removing tabs
    with qtbot.waitSignal(viewspace.numTabsChanged):
        view.removeTab(1)
    assert view.tabs.count() == 2
    assert [view.tabs.tabText(i) for i in range(2)] == ["3", "2"]
    assert [view.stack.widget(i).idx for i in range(2)] == [3, 2]

    # view.setTabModified(0, True)
    # assert view.tabs.tabIcon(0).name() == "document-save"
    # assert view.tabs.tabIcon(1).name() == ""

    view.removeTab(0)
    assert len(view.widgets()) == 1
    view.removeTab(0)
    assert len(view.widgets()) == 0


def test_view_tab_bar(qtbot: QtBot):
    viewspace = ViewSpace()
    qtbot.addWidget(viewspace)
    viewspace.show()
    viewspace.splitActiveHorizontal()
    view = viewspace.views[0]
    tabs = view.tabs

    tabs.view.addTab("1", _TestViewWidget(1, view, editable=True))
    tabs.view.addTab("2", _TestViewWidget(2, view))
    # Test double click rename
    dlg = tabs.tabRenameDialog(0)
    assert dlg.textValue() == "1"
    dlg.textValueSelected.emit("3")
    dlg.close()
    assert tabs.tabText(0) == "3"
    # Rename on non editable will not open dialog
    assert tabs.tabRenameDialog(1) is None

    # Test drag and drop same bar
    with qtbot.assertNotEmitted(tabs.view.numTabsChanged, wait=100):
        qtbot.mousePress(tabs, QtCore.Qt.LeftButton, pos=tabs.tabRect(0).center())
        qtbot.mouseRelease(tabs, QtCore.Qt.LeftButton, pos=tabs.tabRect(1).center())
    assert tabs.tabText(0) == "3"
    assert tabs.tabText(1) == "2"
    # Test drag and drop to new bar / view
    # Broken in QTest


# def test_view_title_bar(qtbot: QtBot):
#     viewspace = ViewSpace()
#     qtbot.addWidget(viewspace)
#     viewspace.show()
#     viewspace.splitActiveHorizontal()

#     # Blocking
#     qtbot.mouseClick(viewspace.views[1].titlebar.split_button, QtCore.Qt.LeftButton)
#     viewspace.view
#     assert viewspace.views[1].active
