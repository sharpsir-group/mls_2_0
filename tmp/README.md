# Temporary/Auxiliary Files Directory

This folder is designated for **auxiliary scripts, documentation, and temporary files** generated during development and data analysis.

## Purpose

When generating auxiliary files (scripts, markdown documentation, data exports, etc.), place them in this `tmp/` directory rather than cluttering the main project structure.

## Usage Guidelines

- ✅ **DO** place here:
  - Temporary analysis scripts
  - Generated documentation files
  - Data export scripts
  - One-off utility scripts
  - Temporary markdown files
  - JSON/CSV exports

- ❌ **DON'T** place here:
  - Core project code
  - Production scripts
  - Permanent documentation (use `docs/` instead)

## File Organization

- Scripts: `tmp/*.py`
- Documentation: `tmp/*.md` or `tmp/*.txt`
- Data exports: `tmp/*.json`, `tmp/*.csv`
- Logs: `tmp/*.log`

## Git

The `.gitkeep` file ensures this directory is tracked in git, but generated files should be ignored (see `.gitignore`).
