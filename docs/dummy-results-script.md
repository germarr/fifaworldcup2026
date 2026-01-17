# Dummy Results Script

Generate simulated FIFA World Cup 2026 match results for testing purposes.

## Overview

The `generate_dummy_results.py` script simulates tournament results to test how the application behaves when actual match results come in. It:

- Generates random scores for matches
- Calculates group standings from actual results
- Resolves knockout bracket teams based on group stage outcomes
- Propagates winners through knockout rounds
- Triggers scoring calculations for all user predictions

## Prerequisites

Ensure you have:

1. The database initialized with all 104 matches
2. All 48 teams assigned to their groups
3. Group stage matches have `home_team_id` and `away_team_id` set

## Usage

Run from the project root directory:

```bash
# Generate results for ALL matches (full tournament simulation)
python -m app.scripts.generate_dummy_results --all

# Generate results for a specific round only
python -m app.scripts.generate_dummy_results --round group_stage
python -m app.scripts.generate_dummy_results --round round_of_32
python -m app.scripts.generate_dummy_results --round round_of_16
python -m app.scripts.generate_dummy_results --round quarter_final
python -m app.scripts.generate_dummy_results --round semi_final
python -m app.scripts.generate_dummy_results --round third_place
python -m app.scripts.generate_dummy_results --round final

# Reset all results (clears actual scores and prediction points)
python -m app.scripts.generate_dummy_results --reset

# Use a seed for reproducible results
python -m app.scripts.generate_dummy_results --all --seed 42

# View current group standings
python -m app.scripts.generate_dummy_results --standings

# View third-place team rankings
python -m app.scripts.generate_dummy_results --thirds

# Quiet mode (less output)
python -m app.scripts.generate_dummy_results --all --quiet
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--all` | Generate results for all 104 matches |
| `--round <name>` | Generate results for a specific round |
| `--reset` | Clear all actual results and reset prediction points |
| `--seed <n>` | Set random seed for reproducible results |
| `--standings` | Display current group standings |
| `--thirds` | Display third-place team rankings |
| `--quiet`, `-q` | Suppress detailed match-by-match output |

## Round Names

| Round | Match Numbers | Description |
|-------|---------------|-------------|
| `group_stage` | 1-72 | 48 group stage matches (12 groups x 6 matches) |
| `round_of_32` | 73-88 | 16 Round of 32 matches |
| `round_of_16` | 89-96 | 8 Round of 16 matches |
| `quarter_final` | 97-100 | 4 Quarter Final matches |
| `semi_final` | 101-102 | 2 Semi Final matches |
| `third_place` | 103 | Third Place match |
| `final` | 104 | Final match |

## How It Works

### Group Stage

1. Generates random scores (0-4 goals each team)
2. Allows draws
3. Updates `actual_home_score`, `actual_away_score`, `status = "completed"`
4. Triggers `calculate_match_points()` for all predictions

### Knockout Bracket Resolution

After group stage completes:

1. Calculates standings for each group (Points > Goal Diff > Goals Scored)
2. Identifies group winners (1st place) and runners-up (2nd place)
3. Ranks all 12 third-place teams
4. Top 8 third-place teams qualify for Round of 32
5. Assigns teams to knockout match slots:
   - `1A` = Group A winner
   - `2B` = Group B runner-up
   - `3-1` = Best third-place team
   - etc.

### Knockout Matches

1. Generates random scores (0-3 goals each team)
2. If draw (~20% of matches), simulates penalty shootout (random winner)
3. Sets `actual_winner_team_id` for bracket progression
4. Assigns winners to next round's matches
5. Semi-final losers go to third-place match
6. Semi-final winners go to final

## Example Workflow

### Full Tournament Simulation

```bash
# Generate all results at once
python -m app.scripts.generate_dummy_results --all

# Check the results page
# Navigate to http://localhost:8000/results
```

### Incremental Simulation

Simulate tournament day-by-day:

```bash
# Day 1: Generate group stage
python -m app.scripts.generate_dummy_results --round group_stage

# Check standings
python -m app.scripts.generate_dummy_results --standings

# Day 2: Round of 32
python -m app.scripts.generate_dummy_results --round round_of_32

# Continue through knockout rounds...
python -m app.scripts.generate_dummy_results --round round_of_16
python -m app.scripts.generate_dummy_results --round quarter_final
python -m app.scripts.generate_dummy_results --round semi_final
python -m app.scripts.generate_dummy_results --round third_place
python -m app.scripts.generate_dummy_results --round final
```

### Testing with Same Results

Use `--seed` for reproducible testing:

```bash
# Always generates the same results
python -m app.scripts.generate_dummy_results --all --seed 12345

# Reset and regenerate with same seed
python -m app.scripts.generate_dummy_results --reset
python -m app.scripts.generate_dummy_results --all --seed 12345
```

## Database Changes

### Fields Updated

| Table | Field | Change |
|-------|-------|--------|
| `matches` | `actual_home_score` | Set to random score |
| `matches` | `actual_away_score` | Set to random score |
| `matches` | `actual_winner_team_id` | Set for knockout matches |
| `matches` | `status` | Set to "completed" |
| `matches` | `home_team_id` | Set for knockout matches (team assignment) |
| `matches` | `away_team_id` | Set for knockout matches (team assignment) |
| `predictions` | `points_earned` | Calculated based on actual results |

### Reset Behavior

The `--reset` flag:

1. Clears `actual_home_score`, `actual_away_score`, `actual_winner_team_id`
2. Sets `status` back to "scheduled"
3. Resets `points_earned` to 0 for all predictions
4. Clears knockout match team assignments (keeps group stage teams)

## Scoring System

When results are generated, the script triggers scoring:

| Round | Correct Outcome | Exact Score |
|-------|-----------------|-------------|
| Group Stage | 1 point | 3 points |
| Knockout | 2 points (correct winner) | 3 points |

## Troubleshooting

### "Teams not assigned" Warning

If you see this for group stage matches, ensure:

1. All 48 teams exist in `fifa_teams` table
2. Teams have `group_letter` assigned (A-L)
3. Group stage matches have `home_team_id` and `away_team_id` set

### Knockout Teams Not Assigned

Run group stage first before knockout rounds:

```bash
python -m app.scripts.generate_dummy_results --round group_stage
python -m app.scripts.generate_dummy_results --round round_of_32
```

Or use `--all` to run everything in order.

### Resetting Doesn't Clear Team Assignments

This is intentional for group stage matches. Knockout team assignments are cleared on reset.

## Integration with Admin Panel

The script uses the same scoring service as the admin panel (`app/services/scoring.py`). You can:

1. Use the script to generate initial results
2. Manually adjust specific matches via admin panel at `/admin/matches`
3. Points will be recalculated automatically
