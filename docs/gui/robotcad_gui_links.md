# RobotCAD GUI Link Plan

This document explains how the digital-twin console should reference GUI resources from the uploaded RobotCAD / FreeCAD project.

## Purpose

The main Python console should not blindly copy the entire upstream RobotCAD workbench into this repository. Instead, the console should expose links to the relevant RobotCAD GUI screens and document what each screen is expected to do.

This keeps the repository clean while still preserving traceability back to the FreeCAD/RobotCAD source package.

## Source Package

Uploaded source archive:

```text
freecad.robotcad-main.zip
```

Important upstream GUI locations found in the archive:

```text
resources/ui/
resources/icons/
```

The `resources/ui/` folder contains Qt Designer `.ui` forms. These are intended to be loaded or converted by a PySide6/PyQt-based application.

The `resources/icons/` folder contains SVG icons that can be reused by the console navigation buttons, sidebar, or engineering pages.

## Console Link Requirements

The main console should include a FreeCAD/RobotCAD page with links/buttons for:

| Console Link | Purpose | Expected Source |
|---|---|---|
| RobotCAD GUI resources | Opens or lists available RobotCAD `.ui` forms | `resources/ui/` |
| RobotCAD icons | Opens or previews available SVG icons | `resources/icons/` |
| FreeCAD model folder | Points to the user's robot design package | supplied project folder |
| ROS 2 export workflow | Documents/export-launches robot description generation | RobotCAD package workflow |
| URDF/Xacro generation | Links to robot description generation page | RobotCAD functionality |
| RViz/Gazebo launch files | Links to simulation/visualization workflow | RobotCAD-generated package |

## Implementation Guidance for Codex

Codex should create a small registry file in Python such as:

```text
gui/robotcad_links.py
```

That file should define friendly names, descriptions, and relative paths for each RobotCAD GUI resource. The main console should read from this registry when building the FreeCAD/RobotCAD page.

Do not hard-code paths throughout the app. Keep RobotCAD GUI paths centralized.

## Plain-English Explanation

RobotCAD already contains GUI screens made for FreeCAD. Our console does not need to replace them. The console should act like a control desk: it should provide clear buttons that tell the user what each RobotCAD screen is for and where it comes from.

## Safety / Maintainability Note

The RobotCAD GUI screens are design and export aids. They are not safety-rated machine controls. Any button that could eventually command real motion must go through the PLC/safety architecture, not directly through a FreeCAD GUI panel.
