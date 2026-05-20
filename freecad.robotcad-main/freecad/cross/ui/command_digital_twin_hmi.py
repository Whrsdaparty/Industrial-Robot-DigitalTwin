from __future__ import annotations

import FreeCAD as fc
import FreeCADGui as fcgui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets

from ..gui_utils import tr
from ..wb_utils import UI_PATH
from .digital_twin_kinematics import DigitalTwinKinematicsDialog


class DigitalTwinHmi:
    """Digital twin HMI shell that opens linked pages."""

    def __init__(self) -> None:
        self.form = fcgui.PySideUic.loadUi(
            str(UI_PATH / 'digital_twin_hmi_dialog.ui'),
        )
        self.form.setWindowTitle(tr('Industrial Robot Digital Twin HMI'))
        self.form.kinematics_button.clicked.connect(self._open_kinematics_page)
        self.form.maintenance_button.clicked.connect(self._open_maintenance_page)
        self.form.vibration_button.clicked.connect(self._open_vibration_page)
        self.form.documentation_button.clicked.connect(self._open_documentation_page)
        self.form.button_box.rejected.connect(self._on_close)

    def _open_dialog(self, ui_filename: str, title: str) -> None:
        dialog = fcgui.PySideUic.loadUi(str(UI_PATH / ui_filename))
        dialog.setWindowTitle(tr(title))
        if hasattr(dialog, 'button_box'):
            dialog.button_box.rejected.connect(dialog.reject)
            dialog.button_box.accepted.connect(dialog.accept)
        dialog.exec_()

    def _open_kinematics_page(self) -> None:
        dialog = DigitalTwinKinematicsDialog()
        dialog.exec_()

    def _open_maintenance_page(self) -> None:
        self._open_dialog('digital_twin_maintenance.ui', 'Maintenance Monitor')

    def _open_vibration_page(self) -> None:
        self._open_dialog('digital_twin_vibration.ui', 'Vibration Monitor')

    def _open_documentation_page(self) -> None:
        self._open_dialog('digital_twin_documentation.ui', 'Digital Twin Documentation')

    def _on_close(self) -> None:
        self.form.close()

    def exec_(self) -> None:
        self.form.exec_()


class _DigitalTwinHMICommand:
    def GetResources(self):
        return {
            'Pixmap': 'robotcad_overcross_joint.svg',
            'MenuText': tr('Digital Twin HMI'),
            'ToolTip': tr('Open the industrial robot digital twin HMI'),
        }

    def IsActive(self):
        return True

    def Activated(self):
        dialog = DigitalTwinHmi()
        dialog.exec_()


fcgui.addCommand('DigitalTwinHMI', _DigitalTwinHMICommand())
