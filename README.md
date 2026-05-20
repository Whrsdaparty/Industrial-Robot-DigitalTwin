# Industrial Robot Digital Twin

A Python-based engineering console for an industrial robotic arm digital twin. The target machine is a FreeCAD/RobotCAD robotic arm mounted on a servo-driven horizontal linear slide. The project combines CAD/ROS 2 integration, kinematics, safety, electrical design, Allen-Bradley PLC logic, FEM links, maintenance tracking, commissioning, acceptance testing, and machine-management statistics.

This repository is written for two audiences:

1. Engineers and technicians who need to understand the machine, wiring, safety chain, PLC behavior, commissioning sequence, and operating logic.
2. Programmers and Codex agents who need enough structure to extend the application without guessing the intent.

## Current Build Stage

Version: see `VERSION`.
Stage: Phase 1 repository foundation and design shell.

Phase 1 establishes the Python GUI console concept, digital-twin package layout, kinematics requirements, safety relay / E-stop concept circuit, Allen-Bradley Structured Text plan, PLC tag plan, program flowchart, commissioning and acceptance documentation, GitHub version-control handoff plan, Codex continuation prompt, and project-agent instructions.

## Plain-English System Summary

The robot has multiple rotary joints plus one horizontal sliding axis. The slide acts like an extra robot axis. The digital twin should know where each joint is, where the slide is, where the end effector is, what the PLC believes is happening, what ROS 2 is commanding, and whether the real or simulated machine is healthy.

```text
CAD model + PLC state + ROS 2 telemetry + maintenance data + statistics + acceptance evidence = usable engineering digital twin
```

This is not only a 3D viewer. It is intended to become an engineering model that connects mechanical design, electrical design, control logic, safety, maintenance, simulation, commissioning, and documentation.

## Main Console Pages Planned

- Home / project console
- 3D Robot / FreeCAD model
- Manual controls
- Kinematics
- ROS 2 bridge
- Digital twin state
- Electrical schematics
- Safety relay and E-stop circuit
- PLC / ladder / Structured Text
- FEM analysis link and results
- Program flowchart
- BOM
- Maintenance
- MMS / statistics
- Commissioning
- Acceptance testing
- Documentation index
- Settings

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Repository Policy

Keep the repository clean. Commit source code, small configuration files, schematics in text/SVG form, PLC Structured Text and tag CSV files, Markdown documentation, flowcharts, and small examples.

Do not commit virtual environments, Python cache folders, large PDF references, vendor ZIP archives, generated meshes, generated ROS 2 workspaces, large CAD exports, or temporary build folders.

## Safety Notice

The safety relay and E-stop material in this repository is concept-level engineering documentation. It is not a validated safety design. Before any physical machine is energized, the design must be checked against the actual devices, risk assessment, applicable standards, and site safety requirements by qualified personnel.

## Codex Handoff

Use `docs/codex_handoff_prompt.md` when moving this project into Codex. Use `docs/exit_strategy_to_codex.md` if work needs to transition out of ChatGPT and into a repository-based coding workflow.
