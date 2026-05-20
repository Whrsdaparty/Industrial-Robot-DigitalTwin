# Risk Register

Purpose: track engineering, software, and safety risks.

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| R001 | Safety logic error | Injury/equipment damage | Review + simulation + validation |
| R002 | Incorrect kinematics | Motion error | Unit tests + compare against CAD |
| R003 | ROS2 communication failure | Lost control | Heartbeat + watchdog |
| R004 | PLC mismatch | Unexpected motion | Acceptance testing |
| R005 | Documentation drift | Confusion | Changelog enforcement |
| R006 | Git repo clutter | Slow development | Repository policy |
