# Repository Structure

Purpose: explain every top-level folder in plain English.

```text
app/              -> executable GUI application
plc/              -> PLC logic and tags
electrical/       -> schematics and safety circuits
docs/             -> documentation
gui/              -> GUI helpers and registries
digital_twin/     -> machine state and simulation
ros2/             -> ROS2 bridge
maintenance/      -> maintenance logic and records
commissioning/    -> startup and validation procedures
acceptance/       -> FAT/SAT evidence
```

Rule:
Every new folder must include a README explaining purpose and contents.
