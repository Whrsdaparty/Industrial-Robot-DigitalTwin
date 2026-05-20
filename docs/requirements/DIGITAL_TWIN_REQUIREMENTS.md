# Industrial Robot Digital Twin Requirements

## Context
This document defines requirements for the Industrial Robot Arm digital twin in the `Industrial-Robot-DigitalTwin` repository.
It is based on the project goals, existing task plan, and requested functionality for a RobotCAD-style sliding-base robot with FreeCAD GUI, gamepad control, kinematics pages, BOM/electrical documentation, PLC/HMI planning, and condition monitoring.

## 1. System Scope
- Digital twin for an industrial robot arm with a sliding base that travels ±2 ft perpendicular to the y axis.
- The robot model must match RobotCAD conventions and integrate into `Industrial-Robot-DigitalTwin/freecad.robotcad-main`.
- The twin must support local model visualization, kinematic computation, user interaction, and linked GUI pages in the FreeCAD-based interface.
- The system must track and document in-house and out-of-house parts, generate BOM entries and cutsheets, and capture electrical and control architecture.
- The system must plan for both Allen-Bradley and Siemens PLC integration and an HMI workflow.
- Maintenance, runtime usage, vibration sensing, and life prediction must be supported.

## 2. Functional Requirements

### 2.1 Robot Model and Geometry
- Model the robot arm as a RobotCAD-compatible kinematic chain.
- Include a base that can translate left/right by 2 ft along an axis perpendicular to the y axis.
- Preserve coordinate frames and joint axes consistent with RobotCAD and FreeCAD conventions.
- Support export or packaging of the robot model for ROS/URDF if needed via RobotCAD.

### 2.2 GUI Integration
- Provide a main GUI page in `freecad.robotcad-main/resources/ui0` for the digital twin.
- Add a dedicated kinematics page linked from the main GUI.
- Add separate linked pages for:
  - forward kinematics matrix and derivation,
  - inverse kinematics solutions and solution branches,
  - maintenance tracking and life bars,
  - vibration and natural frequency monitoring.

### 2.3 Kinematics and Computation
- Expose forward kinematics calculations for the robot arm.
- Display transformation matrices and coordinate math clearly.
- Accept end-effector coordinates and compute the corresponding joint angles.
- Accept joint-angle values and enumerate all valid inverse kinematics solutions.
- Show joint position outputs, reachable poses, and multiple solution branches where relevant.

### 2.4 Control Interfaces
- Integrate gamepad control using `https://github.com/kehuanjack/Gamepad_PiPER`.
- Support gamepad mapping for base translation, joint motion, and mode selection.
- Provide a control pathway from user input to robot actuation commands in the GUI or underlying model.

### 2.5 Documentation and Version Control
- Maintain version control in the GitHub repository at `https://github.com/Whrsdaparty/Industrial-Robot-DigitalTwin.git`.
- Document design decisions, model parameters, and integration steps in repository documentation.
- Create or update README/roadmap content to reflect digital twin requirements and current progress.

### 2.6 Parts, BOM, and Electrical
- Identify all out-of-house components and map them to supplier literature or specifications.
- Document in-house fabricated parts with cutsheets and part descriptions.
- Generate a BOM that distinguishes out-of-house and in-house items.
- Document electrical diagrams showing motors, protection devices, controllers, SBC/CB, and power distribution.
- Include proper motor protection and control safety elements.

### 2.7 PLC/HMI Planning
- Specify Allen-Bradley and Siemens PLC architecture requirements.
- Define IO mapping, control logic overview, and HMI navigation for key pages.
- Plan HMI screens for kinematics, maintenance, vibration, and status dashboards.
- Ensure the GUI supports the HMI flow and links to diagnostic pages.

### 2.8 Maintenance and Condition Monitoring
- Track runtime hours for motors, bearings, and critical components.
- Define end-of-life thresholds and maintenance intervals.
- Include a maintenance playbook for service actions and scheduled checks.
- Provide wear indicators and life bars in the GUI.
- Use piezo vibration sensing to capture machine vibration and compare against natural frequency to detect wear.

## 3. Non-functional Requirements
- The system must be repository-centric, with all model, GUI, and documentation changes tracked in Git.
- The digital twin must produce engineering-ready outputs suitable for review and validation.
- The user interface must be clear and accessible in FreeCAD/RobotCAD.
- Kinematics pages must clearly present both numeric results and the underlying matrix math.
- The system should support future expansion to ROS and hardware-in-the-loop where applicable.

## 4. Follow-up Actions
- Use `DIGITAL_TWIN_TASK_PLAN.md` as the implementation roadmap.
- Start by reviewing the `freecad.robotcad-main/resources/ui0` GUI structure.
- Then implement the kinematics page and linked matrix documentation.
- Next add gamepad, BOM/electrical, PLC/HMI, and condition monitoring support, in that order.

## 5. Notes
- No PDF file was found in the current workspace; these requirements are derived from project goals and the existing task plan.
- If a specific PDF is available, add it to the workspace so the requirements can be validated against it.
