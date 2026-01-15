# Tournament Data Propagation System

## Overview

This system uses `mockups/group_stage_matches.csv` as the **single source of truth** for all tournament data. Any changes to teams, groups, or matches in the CSV will automatically propagate throughout the entire application.

## Quick Start

### Preview Changes (Dry Run)
```bash
python scripts/propagate_from_csv.py --dry-run
```

### Apply Changes
```bash
python scripts/propagate_from_csv.py
```

### Full Reset and Reseed
```bash
python scripts/propagate_from_csv.py --reset
```

## What Gets Propagated

The propagation script synchronizes the following:

### 1. Teams
- **Add**: New teams in CSV are added to database
- **Update**: Team name or group changes are reflected
- **Remove**: Teams not in CSV are removed from database

### 2. Group Stage Matches
- **Add**: New matches in CSV are added to database
- **Update**: Match details (teams, stadium, time, date) are updated
- **Remove**: Matches not in CSV are removed

### 3. Knockout Bracket
- **Regenerate**: Entire knockout bracket is regenerated based on number of groups
- Automatically creates correct structure for:
  - 8 groups (16 teams) → Standard Round of 16
  - 12 groups (24 teams) → Round of 32 + Round of 16
  - 16 groups (32 teams) → Full Round of 32 + Round of 16

### 4. Group Standings
- **Add**: New teams get standings entries
- **Remove**: Deleted teams have standings removed

## How It Works

### CSV as Source of Truth

The script reads `mockups/group_stage_matches.csv` and extracts:
- **Teams**: Unique teams with their codes and group assignments
- **Groups**: Unique group letters (A, B, C, etc.)
- **Matches**: All group stage matches with metadata

### Dynamic Updates

All hardcoded references have been removed from the codebase:

✅ **Fixed Files**:
- `app/knockout.py:30` - Now uses `standings.keys()` dynamically
- `simulations/simulate_full_tournament.py:96` - Now uses `get_all_groups(session)`
- `templates/quickgame_results.html:356` - Now uses `all_groups` variable from backend
- `app/routers/quickgame.py` - Passes `all_groups` dynamically to templates

### Tournament Config

The `app/tournament_config.py` module provides dynamic functions:
- `get_all_groups(db)` - Returns list of all groups from database
- `get_group_count(db)` - Returns total number of groups
- `generate_knockout_bracket_structure(num_teams)` - Creates knockout structure
- `get_knockout_placeholders(num_groups)` - Generates group placeholders for first knockout round

## Modular Team Management

### Example: Removing 4 Teams

1. **Edit CSV**: Remove 4 teams from `mockups/group_stage_matches.csv`
   - Delete all rows containing those teams
   - Ensure groups still have valid structure

2. **Run Script**:
   ```bash
   python scripts/propagate_from_csv.py --dry-run
   ```

3. **Review Changes**: The script will show:
   ```
   ➖ REMOVE: Team1 (T01) - Group A
   ➖ REMOVE: Team2 (T02) - Group B
   ➖ REMOVE: Match #5 - Group Stage
   ...
   ```

4. **Apply Changes**:
   ```bash
   python scripts/propagate_from_csv.py
   ```

5. **Result**:
   - 4 teams removed from database
   - Associated matches removed
   - Group standings updated
   - Knockout bracket regenerated with correct structure

### Example: Adding a New Group

1. **Edit CSV**: Add matches for Group M
   ```csv
   73,Group Stage - Group M,M,7/1/2026,BEL,Belgium,NED,Netherlands,0,0,FALSE,...
   74,Group Stage - Group M,M,7/1/2026,FRA,France,ITA,Italy,0,0,FALSE,...
   ```

2. **Run Script**: `python scripts/propagate_from_csv.py`

3. **Result**:
   - New teams added to database
   - Group M matches added
   - Knockout bracket regenerated for 13 groups (26 qualifying teams)

## Script Options

### `--dry-run` or `-n`
Preview changes without modifying the database.
```bash
python scripts/propagate_from_csv.py --dry-run
```

### `--reset`
Delete entire database and reseed from CSV.
```bash
python scripts/propagate_from_csv.py --reset
```

⚠️ **WARNING**: `--reset` will delete all data including user predictions!

### `--csv PATH`
Use a different CSV file as source.
```bash
python scripts/propagate_from_csv.py --csv mockups/alternative_tournament.csv
```

## CSV Format

The CSV must have these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `match_number` | Unique match number | `1` |
| `round` | Round name | `Group Stage - Group A` |
| `group` | Group letter | `A` |
| `date` | Match date | `6/11/2026` |
| `team1_code` | Team 1 code (or TBD) | `MEX` |
| `team1_name` | Team 1 name | `Mexico` |
| `team2_code` | Team 2 code (or TBD) | `ZAF` |
| `team2_name` | Team 2 name | `South Africa` |
| `actual_team1_score` | Actual score (optional) | `0` |
| `actual_team2_score` | Actual score (optional) | `0` |
| `is_finished` | Match completed? | `FALSE` |
| `stadium` | Stadium name (optional) | `Mexico City Stadium` |
| `time` | Match time (optional) | `15:00` |
| `datetime` | Full datetime (optional) | `6/11/2026 15:00` |

### TBD Teams

For teams not yet qualified, use `TBD` as the code:
```csv
2,Group Stage - Group A,A,6/11/2026,KOR,South Korea,TBD,DEN/MKD/CZE/IRL,0,0,FALSE,...
```

The `team2_name` can contain the qualification path for reference.

## Workflow Integration

### During Development
```bash
# Make changes to CSV
vim mockups/group_stage_matches.csv

# Preview changes
python scripts/propagate_from_csv.py --dry-run

# Apply changes
python scripts/propagate_from_csv.py

# Verify
python -c "from sqlmodel import Session, select, func; from app.database import engine; from app.models import Team, Match; ..."
```

### Before Deployment
```bash
# Full reset to ensure clean state
python scripts/propagate_from_csv.py --reset

# Run tests
pytest tests/
```

### Regular Maintenance
```bash
# Update match results
python mockups/import_group_results_csv.py

# Sync any team changes
python scripts/propagate_from_csv.py --dry-run
python scripts/propagate_from_csv.py
```

## Troubleshooting

### "Match #X not found in database"
- The match number in CSV doesn't exist in database
- Run with `--reset` to rebuild from scratch

### "Team code ABC not found"
- A match references a team that's not in the CSV
- Check CSV for consistency

### Knockout bracket issues
- Ensure all groups have the same number of teams (ideally 4)
- Verify that the number of groups makes sense (8, 12, or 16)

## Best Practices

1. **Always use dry-run first**: Preview changes before applying
2. **Keep CSV consistent**: Ensure all matches reference valid teams
3. **Backup database**: Before major changes, backup `worldcup.db`
4. **Version control CSV**: Track changes to CSV in git
5. **Test after changes**: Run the app to verify everything works

## Architecture

```
CSV File (Source of Truth)
    ↓
propagate_from_csv.py
    ↓
    ├─→ Teams Table
    ├─→ Matches Table (Group Stage)
    ├─→ Matches Table (Knockout - Generated)
    └─→ Group Standings Table
        ↓
    Dynamic Code (No hardcoded values)
        ↓
        ├─→ app/knockout.py (uses standings.keys())
        ├─→ app/standings.py (uses get_all_groups())
        ├─→ simulations/simulate_full_tournament.py (uses get_all_groups())
        └─→ templates/*.html (uses all_groups variable)
```

## Future Enhancements

- [ ] Support for CSV validation before propagation
- [ ] Automatic backup before applying changes
- [ ] Support for updating match results from CSV
- [ ] Integration with CI/CD pipeline
- [ ] Web UI for CSV editing

## Related Files

- `scripts/propagate_from_csv.py` - Main propagation script
- `mockups/group_stage_matches.csv` - Source of truth CSV
- `app/tournament_config.py` - Dynamic tournament configuration
- `simulations/seed_data.py` - Database seeding (uses CSV)
- `mockups/import_group_results_csv.py` - Import match results from CSV

## Support

For issues or questions, refer to:
- [TOURNAMENT_EXPANSION_SUMMARY.md](TOURNAMENT_EXPANSION_SUMMARY.md) - Details on 48-team expansion
- Project documentation in `/docs`
- GitHub issues: https://github.com/your-repo/issues
