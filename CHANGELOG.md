# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-04-17
### Added
- **Modular Architecture**: Split the monolithic `main.py` into a package structure (`src/netcord/`).
- **Unit Tests**: Added initial tests for core network logic and utility functions.
- **Documentation**: Comprehensive README, requirements.txt, and this changelog.

### Changed
- Improved code organization and maintainability.
- Updated build script (`netcord.spec`) for the new structure.

## [1.0.0] - Initial Release
### Added
- Functional IPv4 Network Manager for Windows.
- Discord-inspired dark theme UI with CustomTkinter.
- Support for Static IP, DHCP, and secondary IPs.
- Basic diagnostic tools (Ping, DNS Flush, DHCP Renew).
- Profile management system.
