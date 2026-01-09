# Debug Files

This folder contains debugging and testing scripts used during development and troubleshooting.

## Files

- **debug_final.py** - Debugging script for Match 64 and winner resolution logic. Tests actual vs predicted match outcomes and knockout stage calculations.

- **debug_matches_v2.py** - Utility to inspect finished knockout matches in the database. Lists all knockout stage matches and their team information.

- **debug_models.py** - Simple schema validation script. Verifies that SQLModel database models can be created successfully.

- **reproduce_issue.py** - Script to reproduce and test specific issues during development. Used for isolated problem verification before fixes.

## Usage

These scripts are typically run individually to debug specific functionality:

```bash
python debug/debug_final.py
python debug/debug_matches_v2.py
python debug/debug_models.py
python debug/reproduce_issue.py
```

They connect directly to the SQLite database and perform read-only or test operations.
