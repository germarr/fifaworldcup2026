# Flag Management System

## Overview

The flag management system automatically maps team codes to country flags from flagcdn.com. When teams are imported from CSV, the system automatically updates the flag mappings.

## How It Works

### Automatic Flag Updates

When you run the `propagate_from_csv.py` script, it now automatically:

1. **Detects New Teams**: Scans all teams in the database
2. **Checks Flag Mappings**: Identifies teams without flag mappings in `app/flags.py`
3. **Maps Country Codes**: Converts team codes (FIFA/ISO alpha-3) to ISO alpha-2 codes for flagcdn.com
4. **Updates File**: Automatically adds missing flag mappings to `app/flags.py`
5. **Sorts & Comments**: Keeps the file organized alphabetically with team name comments

### Usage

```bash
# Preview what flags would be added (dry-run mode)
python scripts/propagate_from_csv.py --dry-run

# Add missing flags automatically
python scripts/propagate_from_csv.py
```

### Example Output

```
============================================================
UPDATING FLAGS MAPPING
============================================================
➕ ADD: ITA → it (Italy)
➕ ADD: TUR → tr (Turkey)

✅ Updated app/flags.py with 2 new flag mappings

Flags: +2
```

## Flag URL Format

Flags are served from flagcdn.com using the format:
```
https://flagcdn.com/w{size}/{country-code}.png
```

Example sizes:
- `w20` - 20px width (small)
- `w80` - 80px width (medium)
- `w160` - 160px width (large)

## Where Flags Appear

Flags are displayed throughout the application:

1. **Group Stage Matches** (`quickgame_groups.html`)
   - Shows team flags next to team codes
   - Displayed in match cards

2. **Knockout Stage** (`quickgame_knockout.html`)
   - Team flags for all knockout matches
   - Winner indicators with flags

3. **Results Page** (`quickgame_results.html`)
   - Champion flag (highlighted)
   - Third place flag
   - All match results with team flags
   - Group standings with flags

## Supported Team Code Formats

The system supports multiple team code formats:

- **ISO 3166-1 alpha-3**: DEU, NLD, CHE, HRV, etc.
- **FIFA codes**: GER, NED, SUI, CRO, etc.
- **UK nations**: ENG (gb-eng), SCO (gb-sct), WAL (gb-wls), NIR (gb-nir)

## Country Code Mappings

The script includes comprehensive mappings for 100+ countries, covering:

- All current World Cup 2026 teams (48 teams)
- FIFA member nations
- Extended list for future tournaments

See `scripts/propagate_from_csv.py` - `iso_alpha3_to_alpha2` dictionary for complete list.

## Manual Flag Management

If you need to add or modify flags manually:

1. **Edit `app/flags.py`**:
   ```python
   FIFA_TO_FLAGCDN = {
       "ARG": "ar",  # Argentina
       "BRA": "br",  # Brazil
       "NEW": "xx",  # New Team
       # ... more entries
   }
   ```

2. **Team Code → Country Code**: Map the 3-letter team code to the 2-letter ISO country code
   - Use flagcdn.com country list for reference
   - Special codes for UK nations: `gb-eng`, `gb-sct`, `gb-wls`, `gb-nir`

3. **Run propagate script**: The script will preserve manual edits and add missing teams

## Troubleshooting

### Flag Not Appearing

1. **Check Database**: Verify team exists in database with correct code
   ```bash
   python -c "from app.database import *; from app.models import Team; from sqlmodel import select
   db = next(get_session())
   teams = db.exec(select(Team)).all()
   for t in teams: print(f'{t.code}: {t.name}')"
   ```

2. **Check Flag Mapping**: Verify mapping exists in `app/flags.py`
   ```bash
   grep "TEAM_CODE" app/flags.py
   ```

3. **Add Mapping**: Run propagate script to auto-add missing mappings
   ```bash
   python scripts/propagate_from_csv.py
   ```

### Unknown Country Code

If a team code can't be mapped automatically:

1. **Check Warning**: Script will show warning for unmapped teams
   ```
   ⚠️  WARNING: No flag mapping found for XYZ (Team Name)
   ```

2. **Add Manual Mapping**:
   - Find correct ISO alpha-2 code from [flagcdn.com](https://flagcdn.com)
   - Edit `scripts/propagate_from_csv.py` → `iso_alpha3_to_alpha2` dictionary
   - Add entry: `'XYZ': 'xx'`
   - Re-run script

3. **Fallback**: Team names will still display without flags

## Files Modified

- **`app/flags.py`**: Contains the `FIFA_TO_FLAGCDN` dictionary
- **`scripts/propagate_from_csv.py`**: Automated flag management logic
- **Templates**: Display flags using `flag_url()` function

## API Reference

### `flag_url(team_code: str | None, size: int) -> str | None`

Generates flagcdn.com URL for a team.

**Parameters:**
- `team_code`: 3-letter team code (e.g., "ARG", "BRA")
- `size`: Flag width in pixels (20, 80, 160, etc.)

**Returns:**
- Flag URL string or `None` if mapping not found

**Example:**
```python
from app.flags import flag_url

# Get Argentina flag at 80px width
url = flag_url("ARG", 80)
# Returns: "https://flagcdn.com/w80/ar.png"
```

## Future Enhancements

Potential improvements:

1. **Fallback Images**: Local fallback flags for offline use
2. **Custom Flags**: Support for custom team flags (e.g., regional teams)
3. **Flag Validation**: Test flag URLs during propagation
4. **Multi-format Support**: SVG flags for better scaling
5. **Cache Management**: Local caching of flag images
