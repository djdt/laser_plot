from PySide6 import QtGui

cyan = {
    10: QtGui.QColor(0xE5, 0xF6, 0xFF),
    20: QtGui.QColor(0xBA, 0xE6, 0xFF),
    30: QtGui.QColor(0x82, 0xCD, 0xFF),
    40: QtGui.QColor(0x33, 0xB1, 0xFF),
    50: QtGui.QColor(0x11, 0x92, 0xE8),
    60: QtGui.QColor(0x00, 0x72, 0xC3),
    70: QtGui.QColor(0x00, 0x53, 0x9A),
    80: QtGui.QColor(0x00, 0x3A, 0x6D),
    90: QtGui.QColor(0x01, 0x27, 0x49),
    100: QtGui.QColor(0x1C, 0x0F, 0x30),
}

gray = {
    10: QtGui.QColor(0xF4, 0xF4, 0xF4),
    20: QtGui.QColor(0xE0, 0xE0, 0xE0),
    30: QtGui.QColor(0xC6, 0xC6, 0xC6),
    40: QtGui.QColor(0xA8, 0xA8, 0xA8),
    50: QtGui.QColor(0x8D, 0x8D, 0x8D),
    60: QtGui.QColor(0x6F, 0x6F, 0x6F),
    70: QtGui.QColor(0x52, 0x52, 0x52),
    80: QtGui.QColor(0x39, 0x39, 0x39),
    90: QtGui.QColor(0x26, 0x26, 0x26),
    100: QtGui.QColor(0x16, 0x16, 0x16),
}

magenta = {
    10: QtGui.QColor(0xFF, 0xF0, 0xF7),
    20: QtGui.QColor(0xFF, 0xD6, 0xE8),
    30: QtGui.QColor(0xFF, 0xAF, 0xD2),
    40: QtGui.QColor(0xFF, 0x7E, 0xB6),
    50: QtGui.QColor(0xEE, 0x53, 0x96),
    60: QtGui.QColor(0xD0, 0x26, 0x70),
    70: QtGui.QColor(0x9F, 0x18, 0x53),
    80: QtGui.QColor(0x74, 0x09, 0x37),
    90: QtGui.QColor(0x51, 0x02, 0x24),
    100: QtGui.QColor(0x2A, 0x0A, 0x18),
}

purple = {
    10: QtGui.QColor(0xF6, 0xF2, 0xFF),
    20: QtGui.QColor(0xE8, 0xDA, 0xFF),
    30: QtGui.QColor(0xD4, 0xBB, 0xFF),
    40: QtGui.QColor(0xBE, 0x95, 0xFF),
    50: QtGui.QColor(0xA5, 0x6E, 0xFF),
    60: QtGui.QColor(0x8A, 0x3F, 0xFC),
    70: QtGui.QColor(0x69, 0x29, 0xC4),
    80: QtGui.QColor(0x49, 0x1D, 0x8B),
    90: QtGui.QColor(0x31, 0x13, 0x5E),
    100: QtGui.QColor(0x1C, 0x0F, 0x30),
}

teal = {
    10: QtGui.QColor(0xD9, 0xFB, 0xFB),
    20: QtGui.QColor(0x9E, 0xF0, 0xF0),
    30: QtGui.QColor(0x3D, 0xDB, 0xD9),
    40: QtGui.QColor(0x08, 0xBD, 0xBA),
    50: QtGui.QColor(0x00, 0x9D, 0x9A),
    60: QtGui.QColor(0x00, 0x7D, 0x79),
    70: QtGui.QColor(0x00, 0x5D, 0x5D),
    80: QtGui.QColor(0x00, 0x41, 0x44),
    90: QtGui.QColor(0x02, 0x2B, 0x30),
    100: QtGui.QColor(0x08, 0x1A, 0x1C),
}

red = {
    10: QtGui.QColor(0xFF, 0xF1, 0xF1),
    20: QtGui.QColor(0xFF, 0xD7, 0xD9),
    30: QtGui.QColor(0xFF, 0xB3, 0xB8),
    40: QtGui.QColor(0xFF, 0x83, 0x89),
    50: QtGui.QColor(0xFA, 0x4D, 0x56),
    60: QtGui.QColor(0xDA, 0x1E, 0x28),
    70: QtGui.QColor(0xA2, 0x19, 0x1F),
    80: QtGui.QColor(0x75, 0x0E, 0x13),
    90: QtGui.QColor(0x52, 0x04, 0x08),
    100: QtGui.QColor(0x2D, 0x07, 0x09),
}

white = QtGui.QColor(0xFF, 0xFF, 0xFF)

light_theme = {
    "background": white,
    "axis": gray[50],
    "grid": gray[20],
    "title": gray[100],
    "text": gray[80],
}

sequential = [purple[70], cyan[50], teal[70], magenta[70], red[50], red[90]]
highlights = [purple[40], cyan[20], teal[40], magenta[40], red[20], red[50]]
