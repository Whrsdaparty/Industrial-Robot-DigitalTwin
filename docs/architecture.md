# Architecture

## Goal
Create a Python/PySide6 engineering console acting as a digital twin for a robotic arm + linear slide.

## Major Subsystems
1. GUI Layer (PySide6)
2. Digital Twin Core
3. Kinematics Engine
4. ROS2 Interface
5. PLC Interface (Allen-Bradley)
6. Electrical Documentation
7. Maintenance & Statistics
8. FEM Interface
9. Commissioning & Acceptance

## Data Flow
Real Robot <-> PLC <-> ROS2 <-> Digital Twin <-> GUI

## Rule
Every subsystem must expose:
- purpose
- inputs
- outputs
- failure modes
- tests
- documentation
