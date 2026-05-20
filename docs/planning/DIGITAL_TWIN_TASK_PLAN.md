# Digital Twin Task Plan

## Overview
This task plan is for the `Industrial-Robot-DigitalTwin` project, focusing on the RobotCAD-style sliding-base robot arm, FreeCAD GUI, gamepad control, kinematics visualization, BOM/electrical documentation, PLC/HMI planning, and condition monitoring.

Refer to `DIGITAL_TWIN_REQUIREMENTS.md` for the derived digital twin requirements.

## Queue and Next Actions
- Review `freecad.robotcad-main/resources/ui0` and capture the current GUI structure.
- Define the sliding-base robot geometry and RobotCAD-compatible kinematics.
- Create the first GUI skeleton page for the digital twin.
- Use `DIGITAL_TWIN_BACKLOG.md` to track the queued implementation tasks.

## Phase 1: Core Robot Model and Integration

1. Define the sliding-base robot geometry in FreeCAD and RobotCAD-compatible format
   - model the base travel range ±2 ft perpendicular to the y axis
   - ensure the arm kinematics match RobotCAD conventions
   - verify joint limits and coordinate frames

2. Integrate the model into `freecad.robotcad-main`
   - review existing robot loader and GUI workflow
   - add or update robot description and assembly definitions
   - connect the robot model to existing FreeCAD UI resources in `resources/ui0`

3. Add gamepad control support
   - document how to clone and install `https://github.com/kehuanjack/Gamepad_PiPER`
   - design control mapping for base travel, joint motion, and mode switching
   - plan integration points between gamepad input and the FreeCAD robot control layer

## Phase 2: Kinematics GUI and Math

1. Create a main kinematics GUI page
   - show forward kinematics matrix derivation and notation
   - provide input fields for end-effector coordinates
   - display calculated joint angles and solution sets

2. Add an inverse kinematics input page
   - accept joint-angle values
   - compute reachable end-effector poses
   - enumerate multiple inverse kinematics solutions when applicable

3. Add separate linked pages for matrix explanations
   - forward kinematics equations and transformation matrices
   - inverse kinematics derivation and solution branches

## Phase 3: Documentation, BOM, and Parts Tracking

1. Create BOM and cutsheet documentation
   - identify in-house designed parts and out-of-house components
   - include part descriptions, quantities, specifications, and supplier references
   - generate an in-house parts worksheet/cutsheet

2. Add electrical diagram planning
   - document motor drives, power distribution, controllers, and protection devices
   - include SBC/CB listings and safety elements
   - ensure diagrams include proper protection for motors and control circuits

## Phase 4: PLC/HMI and Controls Architecture

1. Plan Allen-Bradley and Siemens PLC integration
   - specify PLC models, IO mapping, and control architecture
   - define HMI page requirements and navigation from the main GUI
   - plan runtime mode, start/stop, and safety interlocks

2. Create HMI GUI flow
   - link kinematics, maintenance, and vibration pages from the HMI
   - define status dashboards and fault handling screens

## Phase 5: Condition Monitoring and Maintenance

1. Add vibration monitoring page
   - specify piezo sensor placement and signal inputs
   - calculate natural frequencies for motors and mechanics
   - track wear indicators, vibration levels, and remaining life bars

2. Add maintenance and usage tracking
   - track running hours per component
   - define end-of-life thresholds for motors, bearings, and controllers
   - include maintenance playbook actions and scheduled service items

## Phase 6: Review and Version Control

1. Keep all design artifacts in Git
   - use meaningful commits for model, UI, and documentation changes
   - document decisions in README or project notes

2. Review and refine GUI workflow
   - validate page navigation, user inputs, and output clarity
   - ensure engineering documentation is complete and linked

## Next steps
- Start by reviewing `freecad.robotcad-main/resources/ui0` and the existing GUI layout
- Draft the kinematics page and related matrix documentation
- Define the gamepad integration approach and PLC/HMI link points
