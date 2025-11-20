Test harness (removable)

This folder will contain simulated telescope data, test generators, and pytest test suites. You can delete or exclude this folder when running against real hardware.

Planned layout:
- `test_data/` - raw simulated data files (binary/CSV/NumPy)
- `generators/` - scripts that generate synthetic telescope streams
- `unit/` - unit tests against core modules using simulated data
- `integration/` - higher-level integration tests and end-to-end checks
