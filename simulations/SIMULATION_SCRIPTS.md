# FIFA World Cup Simulation Scripts

This document explains the two simulation scripts and their purposes.

---

## Overview

The application has **TWO separate simulation systems**:

### 1. **Actual Match Results** (`simulations/simulate_full_tournament.py`)
- Simulates the **official tournament results**
- Fills in `actual_team1_score` and `actual_team2_score` in the **Match** table
- Used as the "ground truth" that user predictions are compared against

### 2. **User Predictions** (`mockups/generate_user_picks.py`)
- Generates **random predictions for a specific user**
- Creates records in the **Prediction** table
- Simulates what a user might predict for all matches

---

## Database Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Match Table                       │
│  - Stores ALL 64 matches (group + knockout)         │
│  - Contains ACTUAL results when tournament is played │
│  - Fields: actual_team1_score, actual_team2_score   │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Foreign Key: match_id
                   │
                   ▼
        ┌──────────────────────┐
        │  Prediction Table    │
        │  - One per user per  │
        │    match             │
        │  - User's guesses    │
        └──────────────────────┘
```

**Key Point:** Both actual results and predictions reference the **SAME Match records**, ensuring they're comparing the same games with the same teams.

---

## Script 1: `simulations/simulate_full_tournament.py`

### Purpose
Simulates the entire World Cup tournament with random results (the "official" results).

### What It Does
1. **Resets all actual scores** in the Match table
2. **Simulates group stage** (48 matches) with random scores (0-3 goals)
3. **Updates official standings** (GroupStanding table)
4. **Resolves knockout teams** based on group standings
5. **Simulates knockout rounds** (16 matches) ensuring no ties
6. **Sets `is_finished = True`** for all matches

### Usage
```bash
python simulations/simulate_full_tournament.py
```

### Output Example
```
Simulating group stage match 1: Qatar vs Ecuador -> 0-2
Simulating group stage match 2: Senegal vs Netherlands -> 1-3
...
Group Stage Complete!
Official Standings Updated!

Simulating knockout match 49: Netherlands vs Senegal -> 2-1
Simulating knockout match 50: Argentina vs Poland -> 3-0
...
Tournament Simulation Complete! ✓
```

### Database Changes
- **Match table**: Updates `actual_team1_score`, `actual_team2_score`, `is_finished`
- **Match table**: Updates `team1_id`, `team2_id` for knockout matches
- **GroupStanding table**: Recalculates all standings

---

## Script 2: `mockups/generate_user_picks.py` (NEW!)

### Purpose
Generates random predictions for a specific user (simulates a user making picks).

### What It Does
1. **Finds the specified user** by username
2. **Optionally clears existing predictions** (with `--clear` flag)
3. **Generates random predictions** for all matches:
   - Group stage: Random scores (0-4 goals)
   - Knockout stage: Random scores (0-3 goals), with penalty shootout if tied
4. **Resolves knockout teams** based on the user's own group predictions
5. **Creates/updates Prediction records** for the user

### Usage
```bash
# Generate predictions for user "admin"
python mockups/generate_user_picks.py admin

# Generate predictions and clear existing ones first
python mockups/generate_user_picks.py admin --clear

# Generate for a different user
python mockups/generate_user_picks.py john
```

### Output Example
```
============================================================
🎯 Generating Random Predictions for User: admin
============================================================

✓ Found user: admin (ID: 1)

============================================================
📝 Generating Predictions...
============================================================

Created  Match # 1 (Group Stage - Group A     ): Qatar                0-2 Ecuador
Created  Match # 2 (Group Stage - Group A     ): Senegal              1-1 Netherlands
...
Created  Match #49 (Round of 16              ): Netherlands          2-1 Senegal
Created  Match #50 (Round of 16              ): Argentina            1-1 Poland                (Penalties: Argentina)
...

============================================================
✅ PREDICTIONS GENERATION COMPLETE
============================================================
Created:  64 new predictions
Updated:  0 existing predictions
Skipped:  0 unresolved matches
Total:    64 predictions saved

✓ All predictions saved for user: admin
```

### Database Changes
- **Prediction table**: Creates/updates records for the specified user
- **Does NOT modify Match table** (predictions are separate from actual results)

---

## Key Differences

| Feature | simulations/simulate_full_tournament.py | mockups/generate_user_picks.py |
|---------|----------------------------------------|-------------------------------|
| **Purpose** | Generate official tournament results | Generate user predictions |
| **Table Modified** | Match (actual_team1_score, actual_team2_score) | Prediction (predicted_team1_score, predicted_team2_score) |
| **Scope** | All matches (one set of results) | All matches for ONE user |
| **Runs per tournament** | Once (to set official results) | Multiple times (once per user) |
| **Knockout resolution** | Based on actual group standings | Based on user's own group predictions |
| **Can be re-run?** | Yes (resets all results) | Yes (with --clear flag) |

---

## Common Workflows

### Scenario 1: Testing Tournament Scoring
```bash
# 1. Simulate the actual tournament
python simulations/simulate_full_tournament.py

# 2. Generate predictions for user "admin"
python mockups/generate_user_picks.py admin

# 3. Generate predictions for user "john"
python mockups/generate_user_picks.py john

# 4. View the app to see scores compared
python main.py
# Navigate to /bracket/view to see points
```

### Scenario 2: Re-testing with New Results
```bash
# 1. Reset and re-simulate tournament
python simulations/simulate_full_tournament.py

# 2. User predictions remain unchanged
# 3. Scores will be recalculated based on new actual results
```

### Scenario 3: Reset User Predictions
```bash
# Clear and regenerate predictions for a user
python mockups/generate_user_picks.py admin --clear
```

---

## Verification That Both Use Same Matches

To verify that actual results and predictions reference the same matches:

```bash
# Open Python shell
python

# Check match and prediction relationship
from sqlmodel import Session, select
from app.database import engine
from app.models import Match, Prediction, User

with Session(engine) as db:
    # Get a match
    match = db.exec(select(Match).where(Match.match_number == 1)).first()
    print(f"Match 1: {match.team1.name} vs {match.team2.name}")
    print(f"Actual Result: {match.actual_team1_score} - {match.actual_team2_score}")

    # Get all predictions for this match
    predictions = db.exec(select(Prediction).where(Prediction.match_id == match.id)).all()

    for pred in predictions:
        user = db.exec(select(User).where(User.id == pred.user_id)).first()
        print(f"{user.username}'s Prediction: {pred.predicted_team1_score} - {pred.predicted_team2_score}")
```

Expected output:
```
Match 1: Qatar vs Ecuador
Actual Result: 0 - 2
admin's Prediction: 1 - 1
john's Prediction: 0 - 3
```

All predictions and actual results reference **Match ID 1** - the same match record!

---

## Important Notes

1. **`simulations/simulate_full_tournament.py` should be run FIRST** to establish actual results
2. **`mockups/generate_user_picks.py` can be run multiple times** for different users
3. **Knockout predictions** depend on group stage predictions being completed first
4. **Both scripts use the same Match records** - predictions are compared against actual scores from the same matches
5. **The scoring system** (app/scoring.py) compares prediction vs actual on a per-match basis
6. **Scripts are organized** - Simulation scripts are in simulations/ folder, testing/mockup scripts are in mockups/ folder

---

## Manual Prediction Entry (Alternative)

Users can also enter predictions manually via:
- **Web UI**: `/bracket` (Game Mode or Individual Mode)
- **API**: `POST /api/predictions` (single prediction) or `POST /api/predictions/bulk` (multiple)

The `mockups/generate_user_picks.py` script is just a convenience tool for testing or quickly filling in predictions.
