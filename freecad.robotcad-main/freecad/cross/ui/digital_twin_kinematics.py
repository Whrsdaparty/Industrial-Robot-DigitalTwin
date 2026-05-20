from __future__ import annotations

import FreeCAD as fc
import FreeCADGui as fcgui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets

from ..gui_utils import tr
from ..ik import ik
from ..wb_utils import UI_PATH, is_link, is_robot, ros_name
from .object_selector_dialog import ObjectSelector


class DigitalTwinKinematicsDialog:
    def __init__(self) -> None:
        self.doc = fc.activeDocument()
        self.form = fcgui.PySideUic.loadUi(str(UI_PATH / 'digital_twin_kinematics.ui'))
        self.form.setWindowTitle(tr('Digital Twin Kinematics'))

        self.form.pick_robot_button.clicked.connect(self._pick_robot)
        self.form.pick_link_button.clicked.connect(self._pick_link)
        self.form.compute_fk_button.clicked.connect(self._compute_fk)
        self.form.compute_ik_button.clicked.connect(self._compute_ik)
        self.form.button_box.rejected.connect(self.form.reject)

        self._load_selection_into_form()
        self._refresh_joint_values()

    def exec_(self) -> int:
        return self.form.exec_()

    def _load_selection_into_form(self) -> None:
        if not self.doc:
            self._set_status(tr('No active document'), error=True)
            return

        selection = fcgui.Selection.getSelection()
        robot = None
        link_name = ''
        for obj in selection:
            if is_robot(obj) and robot is None:
                robot = obj
            elif is_link(obj) and not link_name:
                link_name = obj.Label

        if robot is not None:
            self.form.robot_line_edit.setText(robot.Label)
        if link_name:
            self.form.endeffector_line_edit.setText(link_name)

    def _set_status(self, message: str, error: bool = False) -> None:
        self.form.status_label.setText(message)
        color = 'red' if error else '#1d7a1d'
        self.form.status_label.setStyleSheet(f'color: {color};')

    def _get_robot(self):
        if not self.doc:
            return None
        robot_label = self.form.robot_line_edit.text().strip()
        if robot_label:
            candidates = self.doc.getObjectsByLabel(robot_label)
            for candidate in candidates:
                if is_robot(candidate):
                    return candidate
            return None

        selection = fcgui.Selection.getSelection()
        for obj in selection:
            if is_robot(obj):
                return obj
        return None

    def _get_end_effector(self, robot):
        if not robot:
            return None
        endeffector_name = self.form.endeffector_line_edit.text().strip()
        if not endeffector_name:
            return None
        endeffector_link = robot.Proxy.get_link(endeffector_name)
        if endeffector_link:
            return endeffector_name
        return None

    def _pick_robot(self) -> None:
        if not self.doc:
            return
        dialog = ObjectSelector(self.doc, is_robot, parent=self.form)
        if dialog.exec():
            selected = dialog.get_selected_object()
            if selected and is_robot(selected):
                self.form.robot_line_edit.setText(selected.Label)
                self._refresh_joint_values()

    def _pick_link(self) -> None:
        robot = self._get_robot()
        if not self.doc or not robot:
            self._set_status(tr('Pick a robot first to choose an end-effector'), error=True)
            return

        def filter_func(obj):
            if not is_link(obj):
                return False
            return robot.Proxy.get_link(ros_name(obj)) is not None

        dialog = ObjectSelector(self.doc, filter_func, parent=self.form)
        if dialog.exec():
            selected = dialog.get_selected_object()
            if selected and is_link(selected):
                self.form.endeffector_line_edit.setText(ros_name(selected))
                self._refresh_joint_values()

    def _refresh_joint_values(self) -> None:
        robot = self._get_robot()
        if not robot:
            self.form.joint_angles_text.setPlainText('')
            return

        current_values = robot.Proxy.get_joint_values()
        lines = []
        for joint, quantity in current_values.items():
            units = '°' if joint.Type in ['revolute', 'continuous'] else 'mm'
            value = float(quantity)
            lines.append(f'{ros_name(joint)}: {value:.3f} {units}')

        self.form.joint_angles_text.setPlainText('\n'.join(lines))

    def _format_matrix(self, placement: fc.Placement) -> str:
        matrix = placement.Matrix
        rows = []
        for i in range(4):
            row = [matrix.A[i * 4 + j] for j in range(4)]
            rows.append(' '.join(f'{value:.6f}' for value in row))
        return '\n'.join(rows)

    def _compute_fk(self) -> None:
        robot = self._get_robot()
        if not robot:
            self._set_status(tr('No robot selected'), error=True)
            return

        endeffector = self._get_end_effector(robot)
        if not endeffector:
            self._set_status(tr('No end-effector link selected'), error=True)
            return

        root_link = robot.Proxy.get_root_link()
        if not root_link:
            self._set_status(tr('Robot has no root link'), error=True)
            return

        transform = robot.Proxy.get_transform(ros_name(root_link), endeffector)
        if transform is None:
            self._set_status(tr('Could not compute transform for the selected end-effector'), error=True)
            return

        self.form.fk_matrix_text.setPlainText(self._format_matrix(transform))
        self.form.x_input.setText(f'{transform.Base.x:.3f}')
        self.form.y_input.setText(f'{transform.Base.y:.3f}')
        self.form.z_input.setText(f'{transform.Base.z:.3f}')
        self._set_status(tr('Forward kinematics computed successfully'), error=False)
        self._refresh_joint_values()

    def _compute_ik(self) -> None:
        robot = self._get_robot()
        if not robot:
            self._set_status(tr('No robot selected'), error=True)
            return

        endeffector = self._get_end_effector(robot)
        if not endeffector:
            self._set_status(tr('No end-effector link selected'), error=True)
            return

        try:
            x = float(self.form.x_input.text())
            y = float(self.form.y_input.text())
            z = float(self.form.z_input.text())
        except ValueError:
            self._set_status(tr('Target coordinates must be numbers'), error=True)
            return

        root_link = robot.Proxy.get_root_link()
        if not root_link:
            self._set_status(tr('Robot has no root link'), error=True)
            return

        target = fc.Placement(fc.Vector(x, y, z), fc.Rotation())

        try:
            solutions = ik(
                robot=robot,
                from_link=ros_name(root_link),
                to_link=endeffector,
                target=target,
            )
        except ImportError as exc:
            self._set_status(str(exc), error=True)
            return
        except Exception as exc:
            self._set_status(f'IK error: {exc}', error=True)
            return

        if not solutions:
            self.form.solutions_text.setPlainText(tr('No IK solutions found'))
            self._set_status(tr('IK did not return a solution'), error=True)
            return

        formatted_solutions = []
        joint_names = [ros_name(j) for j in robot.Proxy.get_actuated_joints_to(endeffector)]
        for solution in solutions:
            solution_lines = []
            for name, value in zip(joint_names, solution):
                solution_lines.append(f'{name}: {value:.3f}')
            formatted_solutions.append('; '.join(solution_lines))

        self.form.solutions_text.setPlainText('\n'.join(formatted_solutions))
        self._set_status(tr('Inverse kinematics computed successfully'), error=False)
        self._refresh_joint_values()
