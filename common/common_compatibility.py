#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2022, Grant Drake'

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import QSizePolicy, QTextEdit, Qt
except ImportError:                        
    from PyQt5.Qt import QSizePolicy, QTextEdit, Qt

try:
    qSizePolicy_Minimum = QSizePolicy.Policy.Minimum
    qSizePolicy_Maximum = QSizePolicy.Policy.Maximum
    qSizePolicy_Expanding = QSizePolicy.Policy.Expanding
    qSizePolicy_Preferred = QSizePolicy.Policy.Preferred
    qSizePolicy_Ignored = QSizePolicy.Policy.Ignored
except:
    qSizePolicy_Minimum = QSizePolicy.Minimum
    qSizePolicy_Maximum = QSizePolicy.Maximum
    qSizePolicy_Expanding = QSizePolicy.Expanding
    qSizePolicy_Preferred = QSizePolicy.Preferred
    qSizePolicy_Ignored = QSizePolicy.Ignored

try:
    qTextEdit_NoWrap = QTextEdit.LineWrapMode.NoWrap
except:
    qTextEdit_NoWrap = QTextEdit.NoWrap

try:
    qtDropActionCopyAction = Qt.DropAction.CopyAction
    qtDropActionMoveAction = Qt.DropAction.MoveAction
except:
    qtDropActionCopyAction = Qt.CopyAction
    qtDropActionMoveAction = Qt.MoveAction
