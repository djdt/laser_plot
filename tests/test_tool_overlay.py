from pathlib import Path
import numpy as np
import tempfile

from PySide2 import QtGui, QtWidgets
from pytestqt.qtbot import QtBot

from pewlib.laser import Laser

from pewpew.widgets.laser import LaserViewSpace
from pewpew.widgets.tools.overlays import OverlayTool

from testing import linear_data, rand_data, FakeEvent


def test_overlay_tool(qtbot: QtBot):
    data = np.zeros((10, 10), dtype=[("r", float), ("g", float), ("b", float)])
    data["r"][:, :] = 1.0
    data["g"][:10, :] = 1.0
    data["b"][:, :10] = 1.0

    viewspace = LaserViewSpace()
    qtbot.addWidget(viewspace)
    viewspace.show()
    view = viewspace.activeView()
    view.addLaser(Laser(data, path=Path("/home/pewpew/real.npz")))
    tool = OverlayTool(view.activeWidget())
    view.addTab("Tool", tool)
    qtbot.waitForWindowShown(tool)

    # Test rgb mode
    assert tool.rows.color_model == "rgb"
    tool.comboAdd(1)  # r
    assert np.all(tool.canvas.image.get_array() == (1.0, 0.0, 0.0))

    tool.comboAdd(2)  # g
    assert np.all(tool.canvas.image.get_array()[:10] == (1.0, 1.0, 0.0))
    assert np.all(tool.canvas.image.get_array()[10:] == (1.0, 0.0, 0.0))

    tool.comboAdd(3)  # g
    assert np.all(tool.canvas.image.get_array()[:10, :10] == (1.0, 1.0, 1.0))
    assert np.all(tool.canvas.image.get_array()[10:, :10] == (1.0, 0.0, 1.0))
    assert np.all(tool.canvas.image.get_array()[10:, 10:] == (1.0, 1.0, 0.0))
    assert np.all(tool.canvas.image.get_array()[10:, 10:] == (1.0, 0.0, 0.0))

    # Test cmyk mode
    tool.radio_cmyk.toggle()
    assert tool.rows.color_model == "cmyk"
    assert np.all(tool.canvas.image.get_array()[:10, :10] == (0.0, 0.0, 0.0))
    assert np.all(tool.canvas.image.get_array()[10:, :10] == (0.0, 1.0, 0.0))
    assert np.all(tool.canvas.image.get_array()[10:, 10:] == (0.0, 0.0, 1.0))
    assert np.all(tool.canvas.image.get_array()[10:, 10:] == (0.0, 1.0, 1.0))

    # Check that the rows are limited to 3
    assert tool.rows.max_rows == 3
    assert not tool.combo_add.isEnabled()
    assert tool.rows.rowCount() == 3
    with qtbot.assert_not_emitted(tool.rows.rowsChanged):
        tool.addRow("r")
    assert tool.rows.rowCount() == 3

    # Check color buttons are not enabled
    for row in tool.rows.rows:
        assert not row.button_color.isEnabled()

    # Test any mode
    tool.radio_custom.toggle()
    assert tool.rows.color_model == "any"
    assert tool.combo_add.isEnabled()
    for row in tool.rows.rows:
        assert row.button_color.isEnabled()
    tool.addRow("g")
    tool.rows[3].setColor(QtGui.QColor.fromRgbF(0.0, 1.0, 1.0))
    assert tool.rows.rowCount() == 4

    # Test normalise
    assert np.amin(tool.canvas.image.get_array()) > 0.0
    tool.check_normalise.setChecked(True)
    tool.refresh()
    assert tool.canvas.image.get_array().data.min() == 0.0
    tool.check_normalise.setChecked(False)

    # Test export
    dlg = tool.openExportDialog()

    dlg2 = dlg.selectDirectory()
    dlg2.close()

    with tempfile.NamedTemporaryFile() as tf:
        dlg.export(tf)
        assert Path(tf.name).exists()

    with tempfile.TemporaryDirectory() as td:
        dlg.lineedit_directory.setText(td)
        dlg.lineedit_filename.setText("test.png")
        dlg.check_individual.setChecked(True)
        dlg.accept()
        qtbot.wait(300)
        assert Path(td).joinpath("test_1.png").exists()
        assert Path(td).joinpath("test_2.png").exists()
        assert Path(td).joinpath("test_3.png").exists()

    # Test close
    with qtbot.wait_signal(tool.rows.rowsChanged):
        tool.rows.rows[-1].close()
    assert tool.rows.rowCount() == 3

    # Test hide
    tool.radio_rgb.toggle()
    with qtbot.wait_signal(tool.rows.rows[0].itemChanged):
        tool.rows.rows[0].button_hide.click()
    assert np.all(tool.canvas.image.get_array()[:10, :10] == (0.0, 1.0, 1.0))
    assert np.all(tool.canvas.image.get_array()[10:, :10] == (0.0, 0.0, 1.0))
    assert np.all(tool.canvas.image.get_array()[10:, 10:] == (0.0, 1.0, 0.0))
    assert np.all(tool.canvas.image.get_array()[10:, 10:] == (0.0, 0.0, 0.0))

    dlg = tool.rows[0].selectColor()
    dlg.close()
