# Versioning Policy

This project uses simple semantic versioning with phase labels.

## Format

```text
MAJOR.MINOR.PATCH-phase
```

Example:

```text
0.1.0-phase1
```

## Version Meaning

- MAJOR: deployable product-level changes
- MINOR: new subsystem or feature area
- PATCH: documentation, cleanup, bug fix, or small improvement
- phase: current development stage

## Planned Version Bands

| Version Band | Meaning |
|---|---|
| v0.1.x | Architecture, documentation, governance |
| v0.2.x | GUI shell and navigation |
| v0.3.x | Kinematics and RobotCAD links |
| v0.4.x | Digital twin core |
| v0.5.x | ROS 2 bridge |
| v0.6.x | PLC, safety, schematics |
| v0.7.x | Maintenance, MMS, commissioning |
| v0.8.x | Simulation and FEM |
| v0.9.x | Integration testing |
| v1.0.x | Deployable MVP |

## Required Update Rule

Every major change should update:

1. `VERSION`
2. `CHANGELOG.md`
3. affected documentation
4. related tests, if applicable
