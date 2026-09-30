"""Minimum widths that keep a widget's full text visible, so a dialog can't shrink until it cuts text off.

Call again after a language change: translated text has a different length.
"""

from __future__ import annotations

from PySide6.QtWidgets import QAbstractSpinBox, QLabel, QLayout, QLineEdit

# QLineEdit.sizeHint() is 17 'x' characters wide plus frame, padding and side widgets (icons,
# clear button). Subtracting the characters leaves exactly that chrome.
_LINE_EDIT_HINT_CHARS = 17
_SLACK = 6  # keeps the last glyph clear of the frame on every style


def fit_line_edit_to_placeholder(edit: QLineEdit) -> None:
    edit.ensurePolished()  # apply the stylesheet's padding and border first
    metrics = edit.fontMetrics()
    chrome = edit.sizeHint().width() - metrics.horizontalAdvance("x") * _LINE_EDIT_HINT_CHARS
    edit.setMinimumWidth(chrome + metrics.horizontalAdvance(edit.placeholderText()) + _SLACK)


def fit_spin_box_to_widest_value(spin: QAbstractSpinBox) -> None:
    # A spin box's size hint already measures its widest value with prefix and suffix.
    spin.ensurePolished()
    spin.setMinimumWidth(spin.sizeHint().width())


def reserve_wrapped_label_heights(layout: QLayout, labels: list[QLabel]) -> None:
    """Make the window's minimum height include word-wrapped labels at the narrowest width.

    Qt leaves height-for-width out of a window's minimum size, so a label that wraps to more
    lines when the window is narrow would otherwise squeeze the other rows until their text
    is clipped at the top and bottom. ``labels`` must span the layout's full width.
    """
    for label in labels:
        label.setMinimumHeight(0)
        label.ensurePolished()
    layout.invalidate()
    margins = layout.contentsMargins()
    narrowest = layout.minimumSize().width() - margins.left() - margins.right()
    for label in labels:
        label.setMinimumHeight(label.heightForWidth(narrowest) if label.text() else 0)
