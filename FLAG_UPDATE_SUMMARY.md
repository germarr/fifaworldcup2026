# Flag Update Summary

## Problem Identified

The quickgame templates were not displaying flags for many teams because the `FIFA_TO_FLAGCDN` dictionary in `app/flags.py` only contained 33 teams, but the 2026 World Cup has 48 teams.

**Missing teams included:**
- Austria, Bolivia, Switzerland, Ivory Coast, Colombia, Cape Verde, Curaçao
- Germany (code mismatch: "DEU" vs "GER"), Netherlands ("NLD" vs "NED")
- Algeria, Egypt, Haiti, Italy, Jordan, New Caledonia, Norway, New Zealand
- Panama, Paraguay, Portugal, Scotland, Turkey, Ukraine, Uzbekistan, South Africa

## Solution Implemented

### 1. Manual Flag Updates (`app/flags.py`)

Updated the `FIFA_TO_FLAGCDN` dictionary to include all 48 teams with proper ISO country code mappings:

```python
FIFA_TO_FLAGCDN = {
    "ARG": "ar",  # Argentina
    "AUS": "au",  # Australia
    "AUT": "at",  # Austria
    # ... all 48 teams
    "ZAF": "za"   # South Africa
}
```

**File:** `app/flags.py:1-72`

### 2. Automated Flag Management (`scripts/propagate_from_csv.py`)

Added automatic flag updates to the CSV propagation script:

**New Features:**
- `update_flags_file()` method: Automatically detects and adds missing flag mappings
- `iso_alpha3_to_alpha2` dictionary: Comprehensive mapping of 100+ country codes
- Integrated into propagation workflow (runs after syncing teams)
- Supports both dry-run preview and live updates

**Files Modified:**
- `scripts/propagate_from_csv.py:22-27` - Added imports (re, Optional)
- `scripts/propagate_from_csv.py:46-106` - Added country code mapping dictionary
- `scripts/propagate_from_csv.py:579-683` - Added flag update methods
- `scripts/propagate_from_csv.py:705-706` - Integrated into workflow
- `scripts/propagate_from_csv.py:722` - Added to summary output

**Key Features:**
- ✅ Detects teams without flag mappings
- ✅ Converts FIFA/ISO codes to flagcdn.com format
- ✅ Automatically updates `app/flags.py`
- ✅ Sorts entries alphabetically
- ✅ Adds team name comments
- ✅ Preserves existing manual edits
- ✅ Supports dry-run mode

### 3. Documentation

Created comprehensive documentation:

**`README_FLAGS.md`** - Complete flag management guide including:
- How the automatic system works
- Usage instructions
- Where flags appear in the app
- Troubleshooting guide
- API reference
- Manual management instructions

## Usage

### Preview Changes (Dry Run)
```bash
python scripts/propagate_from_csv.py --dry-run
```

### Apply Changes
```bash
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

## Verification

All 48 teams now have working flag mappings:

```
✓ ARG: Argentina      → https://flagcdn.com/w80/ar.png
✓ BRA: Brazil         → https://flagcdn.com/w80/br.png
✓ DEU: Germany        → https://flagcdn.com/w80/de.png
...
✓ ZAF: South Africa   → https://flagcdn.com/w80/za.png

Summary: 48/48 teams have flags (100%)
```

## Where Flags Appear

Flags are now displayed in:

1. **Group Stage** (`templates/quickgame_groups.html:64-75`)
   - Match cards showing team flags next to team codes

2. **Knockout Stage** (`templates/quickgame_knockout.html:51-78`)
   - All knockout matches with team flags
   - Winner indicators

3. **Results Page** (`templates/quickgame_results.html:221-240`)
   - Champion flag (highlighted with glow effect)
   - Third place flag
   - All group standings with flags
   - All knockout bracket matches with flags

## Technical Details

### Flag URL Generation

Function: `flag_url(team_code: str | None, size: int) -> str | None`

**Location:** `app/flags.py:65-71`

**Usage in templates:**
```python
flag_url(team.code, 80)  # Returns: "https://flagcdn.com/w80/ar.png"
```

**Sizes used:**
- `20px` - Small (results page tables)
- `80px` - Medium (group/knockout cards)
- `160px` - Large (champion display)

### Code Mappings Supported

- **ISO 3166-1 alpha-3**: Standard 3-letter country codes (DEU, NLD, CHE)
- **FIFA codes**: Alternative 3-letter codes (GER, NED, SUI)
- **UK nations**: Special codes (ENG → gb-eng, SCO → gb-sct, WAL → gb-wls)

## Benefits

1. **Complete Coverage**: All 48 teams now have flags (previously 33/48)
2. **Future-Proof**: Automatic updates when adding new teams
3. **Maintainable**: No manual editing of flags.py required
4. **Organized**: Alphabetically sorted with helpful comments
5. **Documented**: Comprehensive guide for future maintenance

## Testing

Tested by:
1. Temporarily removing flags for Italy and Turkey
2. Running script in dry-run mode (correctly detected missing flags)
3. Running script to apply changes (successfully added flags)
4. Verifying all 48 teams have working flag URLs

## Files Changed

- ✅ `app/flags.py` - Updated flag mappings (all 48 teams)
- ✅ `scripts/propagate_from_csv.py` - Added automated flag management
- ✅ `README_FLAGS.md` - Created comprehensive documentation
- ✅ `FLAG_UPDATE_SUMMARY.md` - This summary document

## Next Steps

When adding new teams in the future:

1. Add team to `mockups/group_stage_matches.csv`
2. Run: `python scripts/propagate_from_csv.py`
3. Script automatically:
   - Adds team to database
   - Adds flag mapping to `app/flags.py`
   - Updates all matches and standings

No manual flag management required! 🎉
