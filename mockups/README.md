# FIFA World Cup - Actual Results Management

This folder contains CSV files for managing actual match results during the tournament.

---

## 📋 Files

- **`group_stage_matches.csv`** - All 48 group stage matches with actual scores
- (Future: `knockout_matches.csv` for Round of 16, Quarter Finals, Semi Finals, Third Place, and Final)

---

## 🔄 Workflow: Updating Actual Match Results

### Step 1: Export Current Matches to CSV

```bash
python mockups/export_group_matches_csv.py
```

This creates/updates `mockups/group_stage_matches.csv` with the current state of all group stage matches.

### Step 2: Edit the CSV File

Open `group_stage_matches.csv` in your preferred editor (Excel, Google Sheets, VS Code, etc.)

**Columns to update:**
- `actual_team1_score` - Actual goals scored by team 1
- `actual_team2_score` - Actual goals scored by team 2
- `is_finished` - Set to `TRUE` when match is complete, `FALSE` otherwise

**Example:**
```csv
match_number,round,group,match_date,team1_code,team1_name,team2_code,team2_name,actual_team1_score,actual_team2_score,is_finished
1,Group Stage - Group A,A,2026-01-06,QAT,Qatar,ECU,Ecuador,0,2,TRUE
2,Group Stage - Group A,A,2026-01-06,SEN,Senegal,NED,Netherlands,0,2,TRUE
```

### Step 3: Import Updated Results to Database

**Dry Run (preview changes without saving):**
```bash
python mockups/import_group_results_csv.py --dry-run
```

**Live Import (save changes to database):**
```bash
python mockups/import_group_results_csv.py
```

The import script will:
1. ✅ Update `actual_team1_score` and `actual_team2_score` in the Match table
2. ✅ Update `is_finished` flag
3. ✅ Recalculate official group standings (GroupStanding table)
4. ✅ Show a summary of changes

---

## 📊 CSV File Structure

### group_stage_matches.csv

| Column | Description | Example | Notes |
|--------|-------------|---------|-------|
| `match_number` | Unique match ID | `1` | **Do not edit** |
| `round` | Round name | `Group Stage - Group A` | **Do not edit** |
| `group` | Group letter | `A` | **Do not edit** |
| `match_date` | Match date | `2026-01-06` | **Do not edit** |
| `team1_code` | Team 1 FIFA code | `QAT` | **Do not edit** |
| `team1_name` | Team 1 full name | `Qatar` | **Do not edit** |
| `team2_code` | Team 2 FIFA code | `ECU` | **Do not edit** |
| `team2_name` | Team 2 full name | `Ecuador` | **Do not edit** |
| `actual_team1_score` | Team 1 goals | `0` | **EDIT THIS** (leave empty if not played) |
| `actual_team2_score` | Team 2 goals | `2` | **EDIT THIS** (leave empty if not played) |
| `is_finished` | Match completion | `TRUE` or `FALSE` | **EDIT THIS** |

---

## 🎯 Use Cases

### Use Case 1: Update Results After Each Match Day

```bash
# 1. Export current state
python mockups/export_group_matches_csv.py

# 2. Open CSV and update scores for today's matches
# (Set actual_team1_score, actual_team2_score, is_finished=TRUE)

# 3. Preview changes
python mockups/import_group_results_csv.py --dry-run

# 4. Import to database
python mockups/import_group_results_csv.py
```

### Use Case 2: Bulk Update Multiple Matches

```bash
# 1. Export CSV
python mockups/export_group_matches_csv.py

# 2. Edit multiple matches at once in spreadsheet

# 3. Import all changes
python mockups/import_group_results_csv.py
```

### Use Case 3: Verify Database State

```bash
# Export and check current results without editing
python mockups/export_group_matches_csv.py
cat mockups/group_stage_matches.csv
```

---

## ⚠️ Important Notes

1. **Do NOT edit** the following columns (they are reference data):
   - `match_number`, `round`, `group`, `match_date`
   - `team1_code`, `team1_name`, `team2_code`, `team2_name`

2. **Leave scores empty** for matches that haven't been played yet:
   ```csv
   49,Round of 16,R16,2026-01-15,NED,Netherlands,USA,USA,,,FALSE
   ```

3. **is_finished values:**
   - `TRUE` - Match has been completed (scores are final)
   - `FALSE` - Match has not been played or is in progress

4. **Score values must be integers:**
   - Valid: `0`, `1`, `2`, `3`, etc.
   - Invalid: `2.5`, `two`, `2-3`, etc.

5. **The import script automatically:**
   - Updates the Match table with actual results
   - Recalculates group standings
   - Shows which teams qualify for knockout rounds

---

## 🔗 Related Scripts

- **`mockups/export_group_matches_csv.py`** - Export matches to CSV
- **`mockups/import_group_results_csv.py`** - Import results from CSV
- **`mockups/generate_user_picks.py`** - Generate user predictions (for testing)
- **`simulations/simulate_full_tournament.py`** - Generate random results (for testing)

---

## 🚀 Quick Reference

```bash
# Export matches to CSV
python mockups/export_group_matches_csv.py

# Import with preview (dry run)
python mockups/import_group_results_csv.py --dry-run

# Import and save to database
python mockups/import_group_results_csv.py

# View CSV in terminal
cat mockups/group_stage_matches.csv | column -t -s,
```

---

## 📝 Example: Match Day Workflow

**Scenario:** Group A matches finished today. Qatar beat Ecuador 2-1, and Netherlands drew 1-1 with Senegal.

```bash
# 1. Export current CSV
python mockups/export_group_matches_csv.py

# 2. Edit the CSV file
# Find matches 1 and 2:
# Match 1: Qatar vs Ecuador -> Change to: 2, 1, TRUE
# Match 2: Senegal vs Netherlands -> Change to: 1, 1, TRUE

# 3. Preview changes
python mockups/import_group_results_csv.py --dry-run
# Output:
# 🔍 WOULD UPDATE Match # 1 (QAT vs ECU): --  → 2-1 | Finished: True
# 🔍 WOULD UPDATE Match # 2 (SEN vs NED): --  → 1-1 | Finished: True

# 4. Apply changes
python mockups/import_group_results_csv.py
# Output:
# ✅ UPDATE Match # 1 (QAT vs ECU): --  → 2-1 | Finished: True
# ✅ UPDATE Match # 2 (SEN vs NED): --  → 1-1 | Finished: True
# 💾 Database committed successfully!
# 📊 Updating Official Group Standings...
# ✅ Official standings updated!
```

---

## 🛠️ Future Enhancements

- [ ] Create `knockout_matches.csv` for knockout stage results
- [ ] Add validation script to check CSV integrity
- [ ] Create web UI for uploading CSV files
- [ ] Add API endpoint for CSV import
- [ ] Generate match reports from CSV data
