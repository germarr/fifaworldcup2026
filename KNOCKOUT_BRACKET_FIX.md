# Knockout Bracket Structure Fix

## Summary

Fixed the knockout bracket structure to correctly handle the 48-team World Cup format with 12 groups.

## Problem

The knockout bracket was generating incorrect match numbers:
- **Before**: Round of 32 had only 8 matches (73-80), ending at match 96
- **Expected**: Round of 32 should have 16 matches (73-88), ending at match 104

## Root Cause

The `generate_knockout_bracket_structure()` function had flawed logic that:
1. Added preliminary rounds incorrectly for 32 qualifying teams
2. The `get_knockout_placeholders()` function calculated qualifying teams as `num_groups * 2 = 24` instead of 32

For 12 groups with the 48-team format:
- Top 2 from each group: 24 teams
- Best 8 third-place teams: 8 teams
- **Total**: 32 teams in knockout stage

## Solution

### 1. Fixed `tournament_config.py`

**`generate_knockout_bracket_structure()`** - Simplified logic:
```python
# Old: Complex logic with special cases
# New: Clean while loop handling powers of 2
while current_teams >= 4:
    num_matches = current_teams // 2
    # Assign round names (32, 16, 8, 4)
    rounds.append((round_name, num_matches, match_num, desc))
    current_teams //= 2
```

**`get_knockout_placeholders()`** - Fixed qualifying teams calculation:
```python
# Old: qualifying_teams = num_groups * 2  # Always
# New:
if num_groups == 12:
    qualifying_teams = 32  # Top 2 + 8 third-place
else:
    qualifying_teams = num_groups * 2
```

### 2. Created Migration Script

**File**: `migrations/006_fix_knockout_bracket.py`

- Deletes all existing knockout matches
- Regenerates with correct structure
- Includes dry-run mode for safety

**Usage**:
```bash
# Preview changes
python migrations/006_fix_knockout_bracket.py --dry-run

# Apply changes
python migrations/006_fix_knockout_bracket.py
```

### 3. Updated Propagation Script

The `scripts/propagate_from_csv.py` script now automatically uses the corrected logic when regenerating knockout brackets.

## Correct Structure

### Match Numbering (12 Groups, 32 Knockout Teams)

| Round | Match Numbers | Count | Description |
|-------|---------------|-------|-------------|
| **Round of 32** | 73-88 | 16 | All 32 qualified teams |
| **Round of 16** | 89-96 | 8 | Winners from R32 |
| **Quarter Finals** | 97-100 | 4 | Winners from R16 |
| **Semi Finals** | 101-102 | 2 | Winners from QF |
| **Third Place** | 103 | 1 | Losers from SF |
| **Final** | 104 | 1 | Winners from SF |
| **Total** | 73-104 | 32 | All knockout matches |

### Round of 32 Placeholders

The Round of 32 includes third-place team placeholders:
- `1A`, `2A`: Group A winner/runner-up
- `3ABCDF`: Third-place team from one of groups A, B, C, D, or F
- This allows for the best 8 third-place teams to qualify

**Example matches**:
```
Match 73: 2A vs 2B
Match 74: 1C vs 2F
Match 75: 1E vs 3ABCDF  ← Third-place team
Match 76: 1F vs 2C
...
Match 88: 1K vs 3DEIJL  ← Third-place team
```

## Database State After Fix

```
✅ Teams: 48 (4 per group × 12 groups)
✅ Group Stage Matches: 72
✅ Knockout Matches: 32
✅ Total Matches: 104
```

### Knockout Breakdown
```
Round of 32:     16 matches (73-88)
Round of 16:      8 matches (89-96)
Quarter Finals:   4 matches (97-100)
Semi Finals:      2 matches (101-102)
Third Place:      1 match  (103)
Final:            1 match  (104)
```

## QuickGame Integration

The knockout bracket structure is now correctly reflected in Quick Games:

### Third-Place Ranking
For 12-group tournaments, users must rank the 8 best third-place teams before proceeding to knockout:
- `/quickgame/{code}/third-place` - Ranking interface
- Uses `QuickGameThirdPlaceRanking` model
- Determines which 8 third-place teams qualify

### Placeholder Resolution
The `build_quickgame_placeholder_resolution()` function now correctly:
1. Resolves `1A-1L` (group winners)
2. Resolves `2A-2L` (group runners-up)
3. Resolves `3ABCDF` style placeholders (third-place teams)
4. Resolves `W##` (match winners)

### Template Updates
Templates dynamically handle Round of 32:
```jinja2
{% set round_of_32 = rounds.get('Round of 32', []) %}
{% if round_of_32 %}
  <!-- Show Round of 32 bracket -->
{% endif %}
```

## Testing

### Verify Structure
```bash
python -c "
from sqlmodel import Session, select
from app.database import engine
from app.models import Match

with Session(engine) as session:
    knockout = session.exec(
        select(Match).where(~Match.round.like('Group Stage%')).order_by(Match.match_number)
    ).all()

    for round_name in ['Round of 32', 'Round of 16', 'Quarter Finals', 'Semi Finals', 'Third Place', 'Final']:
        matches = [m for m in knockout if m.round == round_name]
        if matches:
            min_num = min(m.match_number for m in matches)
            max_num = max(m.match_number for m in matches)
            print(f'{round_name}: {len(matches)} matches ({min_num}-{max_num})')
"
```

**Expected Output**:
```
Round of 32: 16 matches (73-88)
Round of 16: 8 matches (89-96)
Quarter Finals: 4 matches (97-100)
Semi Finals: 2 matches (101-102)
Third Place: 1 matches (103-103)
Final: 1 matches (104-104)
```

### Test Propagation
```bash
# Test without changes
python scripts/propagate_from_csv.py --dry-run

# Apply any CSV updates
python scripts/propagate_from_csv.py
```

## Files Modified

1. **app/tournament_config.py**
   - Fixed `generate_knockout_bracket_structure()` logic
   - Fixed `get_knockout_placeholders()` calculation
   - Added proper documentation

2. **migrations/006_fix_knockout_bracket.py** (NEW)
   - Migration script to fix existing databases
   - Supports dry-run mode
   - Deletes and regenerates all knockout matches

3. **scripts/propagate_from_csv.py**
   - Now uses corrected tournament_config functions
   - Automatically generates correct structure

## Related Documentation

- `README_PROPAGATION.md` - How to propagate changes from CSV
- `TOURNAMENT_EXPANSION_SUMMARY.md` - Initial 48-team expansion
- `app/tournament_config.py` - Dynamic tournament configuration

## Future Considerations

### Extensibility
The updated code now cleanly handles:
- **8 groups** (16 teams): Standard Round of 16 format
- **12 groups** (32 teams): Round of 32 with third-place teams
- **16 groups** (32 teams): Standard Round of 32 format
- **Future expansions**: Automatically adjusts to any power-of-2 knockout size

### Third-Place Team Logic
For tournaments with 12 groups, the system correctly:
1. Calculates standings for all groups
2. Identifies third-place teams from each group
3. Ranks them by points, goal difference, etc.
4. Selects best 8 for knockout qualification
5. Maps them to appropriate Round of 32 matches

## Migration History

| Version | Date | Description |
|---------|------|-------------|
| 005 | Earlier | Added match metadata fields |
| 006 | 2026-01-10 | **Fixed knockout bracket structure** |

## Rollback

If needed, rollback by:
1. Restore database backup from before migration
2. Or revert `app/tournament_config.py` changes and run propagation script with old CSV

## Status

✅ **COMPLETE** - All changes applied and tested successfully.
