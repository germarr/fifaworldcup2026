# FIFA World Cup 2026 - Tournament Expansion Summary

## Overview
Successfully expanded the tournament from 8 groups (32 teams) to 12 groups (48 teams) with updated knockout structure.

## Database Changes

### Teams
- **Old**: 32 teams across 8 groups (A-H)
- **New**: 42 teams across 12 groups (A-L)
- Additional 6 teams pending qualification (TBD placeholders in CSV)

### Matches
- **Old**: 64 total matches (48 group + 16 knockout)
- **New**: 96 total matches breakdown:
  - Group Stage: 72 matches
  - Round of 32: 8 matches (new)
  - Round of 16: 8 matches
  - Quarter Finals: 4 matches
  - Semi Finals: 2 matches
  - Third Place: 1 match
  - Final: 1 match

### Groups Structure (12 Groups)

| Group | Teams | Count |
|-------|-------|-------|
| A | MEX, ZAF, KOR | 3 |
| B | CAN, QAT, CHE | 3 |
| C | BRA, HTI, MAR, SCO | 4 |
| D | AUS, PRY, USA | 3 |
| E | CUW, ECU, DEU, CIV | 4 |
| F | JPN, NLD, TUN | 3 |
| G | BEL, EGY, IRN, NZL | 4 |
| H | CPV, SAU, ESP, URY | 4 |
| I | FRA, NOR, SEN | 3 |
| J | DZA, ARG, AUT, JOR | 4 |
| K | COL, PRT, UZB | 3 |
| L | HRV, ENG, GHA, PAN | 4 |

## Schema Updates

### Match Model (app/models.py)
Added three new fields:
- `stadium`: VARCHAR(100) - Stadium name
- `time`: VARCHAR(10) - Match time
- `datetime_str`: VARCHAR(50) - Full datetime string

### Migration Files
1. **migrations/005_add_match_metadata.py** - Added new Match fields
2. **simulations/seed_data.py** - Completely rewritten to:
   - Read teams and matches from CSV
   - Handle 12-group structure
   - Create proper knockout bracket for 48-team format

## Code Updates

### Files Modified
1. **app/standings.py:82** - Updated group loop from "ABCDEFGH" to "ABCDEFGHIJKL"
2. **app/knockout.py:30** - Updated group loop from "ABCDEFGH" to "ABCDEFGHIJKL"
3. **simulations/simulate_full_tournament.py:96** - Updated group initialization

## Knockout Bracket Structure

### Round of 32 (New Addition)
With 24 qualifying teams (top 2 from each of 12 groups):
- **8 teams get byes**: 1A, 1B, 1C, 1D, 1E, 1F, 1G, 1H
- **16 teams play 8 matches**: Remaining group winners and all runners-up

Matchups:
- Match 73: 1I vs 2L
- Match 74: 1J vs 2K
- Match 75: 1K vs 2J
- Match 76: 1L vs 2I
- Match 77: 2A vs 2H
- Match 78: 2B vs 2G
- Match 79: 2C vs 2F
- Match 80: 2D vs 2E

### Round of 16
8 matches with bye teams facing R32 winners:
- Match 81: 1A vs W73
- Match 82: 1B vs W74
- Match 83: 1C vs W75
- Match 84: 1D vs W76
- Match 85: 1E vs W77
- Match 86: 1F vs W78
- Match 87: 1G vs W79
- Match 88: 1H vs W80

### Quarter Finals → Semi Finals → Final
Standard progression from 8 teams down to 1 champion.

## Data Sources

### Primary Source
**mockups/group_stage_matches.csv** - Contains:
- 72 group stage matches
- Complete team information
- Match dates, times, stadiums
- TBD placeholders for qualifying teams

### Important Data Fixes
1. **Japan**: Consolidated from JPN/JAP to JPN
2. **Scotland**: Changed from GBR to SCO
3. **England**: Changed from GBR to ENG

## Testing & Verification

### Database Seeding
Run: `python simulations/seed_data.py`

Creates fresh database with:
- ✅ 42 teams
- ✅ 96 matches
- ✅ 12 groups
- ✅ Complete knockout bracket
- ✅ All metadata (stadium, time, datetime)

### Verification Commands
```bash
# Check database stats
python -c "from sqlmodel import Session, select, func; from app.database import engine; from app.models import Team, Match; ..."

# Run migrations
python migrations/005_add_match_metadata.py

# Seed database
python simulations/seed_data.py
```

## Migration Path

### From Old Database
1. Delete old database: `rm worldcup.db`
2. Run seed script: `python simulations/seed_data.py`
3. Verify: Check team/match counts

### Key Differences
- No more hardcoded 32-team structure
- Dynamic CSV-based seeding
- Expandable to handle TBD teams as they qualify
- Proper 48-team knockout bracket

## Future Considerations

### TBD Teams
6 teams in CSV marked as TBD with qualification paths:
- DEN/MKD/CZE/IRL
- ITA/NIR/WAL/BIH
- TUR/ROU/SVK/KOS
- UKR/SWE/POL/ALB
- BOL/SUR/IRQ
- NCL/JAM/COD

These will be resolved once qualification completes.

### Match Scheduling
Dates currently set to:
- Group Stage: June 11-27, 2026
- Round of 32: June 29, 2026
- Round of 16: July 1, 2026
- Quarter Finals: July 4, 2026
- Semi Finals: July 8, 2026
- Third Place: July 11, 2026
- Final: July 12, 2026

## Status
✅ **COMPLETE** - All data propagated successfully throughout the application.
