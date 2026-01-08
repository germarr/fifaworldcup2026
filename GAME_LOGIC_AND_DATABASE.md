# FIFA World Cup Prediction Game - Game Logic & Database Guide

## Overview

This document explains how the FIFA World Cup Prediction Game works, including:
- **Game Logic**: How winners/losers are determined for group stage and knockout matches
- **Database Schemas**: The tables that store teams, matches, predictions, and standings
- **Point System**: How user predictions are scored
- **Data Flow**: How all components interact with each other

---

## 1. Database Architecture

### High-Level Overview

The application uses **SQLite** with 8 main tables that work together to manage tournament predictions:

```
┌─────────────────────────────────────────────────────────────┐
│                     TOURNAMENT DATA                          │
│  (Teams, Matches, Group Standings - "ground truth")          │
├─────────────────────────────────────────────────────────────┤
│  • Teams (32 World Cup teams)                                │
│  • Matches (64 total: 48 group stage + 16 knockout)         │
│  • GroupStanding (actual group standings)                   │
└─────────────────────────────────────────────────────────────┘
              ↓                ↓
┌──────────────────────┐  ┌─────────────────────────┐
│  USER PREDICTIONS    │  │  USER MANAGEMENT        │
│  (Per-user bracket)  │  │  (Authentication, team) │
├──────────────────────┤  ├─────────────────────────┤
│ • Predictions        │  │ • Users                 │
│  (user's guesses)    │  │ • Sessions              │
│                      │  │ • PlayerTeam            │
│                      │  │ • UserTeamMembership    │
└──────────────────────┘  └─────────────────────────┘
```

### Table Details

#### 1. **Teams** (32 World Cup teams)
```sql
Table: teams
├── id (PK)              → Team unique identifier
├── name                 → "Brazil", "Argentina", etc.
├── code                 → "BRA", "ARG" (3-letter code)
├── group                → "A", "B", "C", ... "H"
└── flag_url             → URL to team flag image
```

**Purpose**: Stores all 32 World Cup teams and their group assignments.

#### 2. **Matches** (64 tournament matches)
```sql
Table: matches
├── id (PK)                      → Match unique identifier
├── round                        → "Group Stage - Group A", "Round of 16", "Semi-Final", "Final"
├── match_number                 → 1-64 (sequential order)
├── team1_id (FK→teams.id)       → Home/First team (NULL for knockout before prediction)
├── team2_id (FK→teams.id)       → Away/Second team (NULL for knockout before prediction)
├── team1_placeholder            → "1A", "2B" (group winner/runner-up) or "W49" (match winner)
├── team2_placeholder            → Similar placeholder for team2
├── match_date                   → When the match is/was scheduled
├── actual_team1_score           → Actual goals scored by team1 (NULL until match is finished)
├── actual_team2_score           → Actual goals scored by team2 (NULL until match is finished)
├── actual_team1_penalty_score   → Penalty shootout result (for knockout ties)
├── actual_team2_penalty_score   → Penalty shootout result (for knockout ties)
├── penalty_winner_id (FK→teams) → Winner of penalty shootout (for ties in knockout)
└── is_finished                  → Boolean (true = match result known)
```

**Purpose**: Stores all tournament matches with results.

**Key Points**:
- **Group Stage matches** have direct `team1_id` and `team2_id` (teams are known)
- **Knockout matches** use placeholders (`team1_placeholder`, `team2_placeholder`) because teams aren't determined until previous rounds finish

#### 3. **Predictions** (User predictions per match)
```sql
Table: predictions
├── id (PK)
├── user_id (FK→users.id)            → Which user made this prediction
├── match_id (FK→matches.id)         → Which match they're predicting
├── predicted_team1_score            → User's guess for team1's score
├── predicted_team2_score            → User's guess for team2's score
├── predicted_winner_id (FK→teams)   → Explicit winner choice (handles ties/penalties)
├── penalty_shootout_winner_id       → User's penalty shootout prediction
├── created_at                       → When prediction was created
└── updated_at                       → When prediction was last updated
```

**Purpose**: Stores each user's prediction for each match.

**Key Points**:
- One prediction per user per match
- Contains both score predictions and winner predictions
- Predictions are user-specific (two users can predict different outcomes)

#### 4. **GroupStanding** (Tournament standings)
```sql
Table: group_standings
├── id (PK)
├── group_letter                 → "A", "B", etc.
├── team_id (FK→teams.id)        → Which team
├── played                       → Matches played
├── won                          → Wins
├── drawn                        → Draws
├── lost                         → Losses
├── goals_for                    → Goals scored
├── goals_against                → Goals conceded
├── goal_difference              → goals_for - goals_against
├── points                       → Total points in group
└── updated_at                   → Last update time
```

**Purpose**: Stores the actual tournament group standings (reference data).

#### 5. **Users** (Player accounts)
```sql
Table: users
├── id (PK)
├── username                 → Unique login name
├── password_hash           → Hashed password
├── email                   → Email address
├── first_name              → User's first name
├── last_name               → User's last name
├── favorite_team_id (FK→teams) → User's favorite World Cup team
├── avatar_seed             → Avatar generation seed
├── total_points            → Cached total score
├── player_team_id (FK→player_teams) → Deprecated (team membership)
├── cookie_consent          → GDPR consent
└── created_at              → Account creation date
```

**Purpose**: Stores user account information and profile data.

#### 6. **UserTeamMembership** (Many-to-many: users ↔ player teams)
```sql
Table: user_team_memberships
├── id (PK)
├── user_id (FK→users.id)              → Which user
├── player_team_id (FK→player_teams.id) → Which team they joined
└── joined_at                           → When they joined
```

**Purpose**: Allows multiple users to join a player team (competition team).

#### 7. **PlayerTeam** (Competition teams)
```sql
Table: player_teams
├── id (PK)
├── name                    → Team name (e.g., "Office Team")
├── join_code              → Code to join (e.g., "ABC123")
└── created_at             → Creation date
```

**Purpose**: Allows users to form teams and compete together.

#### 8. **Sessions** (Authentication)
```sql
Table: sessions
├── id (PK)
├── user_id (FK→users.id)
├── session_token          → Unique session identifier
├── created_at
└── expires_at
```

**Purpose**: Manages user login sessions.

---

## 2. Data Relationships & Flow

### Entity Relationship Diagram

```
teams
  ├─ 1 ─→ N ─ matches (team1_id)
  ├─ 1 ─→ N ─ matches (team2_id)
  ├─ 1 ─→ N ─ group_standings
  └─ 1 ─→ N ─ users (favorite_team_id)

matches
  └─ 1 ─→ N ─ predictions

users
  ├─ 1 ─→ N ─ predictions
  ├─ 1 ─→ N ─ sessions
  ├─ 1 ─→ N ─ user_team_memberships
  └─ 0-1 ─→ 1 ─ player_teams (deprecated)

player_teams
  └─ 1 ─→ N ─ user_team_memberships

group_standings
  └─ N ─→ 1 ─ teams
```

### Data Flow Example: Group Stage Match

**Scenario**: User predicts Brazil (1A) vs Mexico (2B) in Round of 16

**Step 1: Create Prediction**
```
User makes prediction:
  Brazil 3 - 1 Mexico (predicted Brazil to win)
  
Stored in:
  predictions {
    user_id: 5,
    match_id: 49,  // Round of 16, Match 1
    predicted_team1_score: 3,
    predicted_team2_score: 1,
    predicted_winner_id: 1  // Brazil's team_id
  }
```

**Step 2: Match Completes**
```
Actual result:
  Brazil 3 - 1 Mexico ✓ (User was correct!)
  
Updated in:
  matches {
    id: 49,
    actual_team1_score: 3,
    actual_team2_score: 1,
    is_finished: true,
    penalty_winner_id: NULL  // No penalties needed
  }
```

**Step 3: Points Calculation**
```
calculate_match_points(prediction, match) returns:
  {
    points: 3,
    breakdown: ["Correct Outcome (+1)", "Exact Score (+2)"],
    status: "complete"
  }

User total points updated in:
  users {
    id: 5,
    total_points: 23  // Updated with new points
  }
```

---

## 3. Game Logic: Determining Winners & Losers

### 3.1 Group Stage Matches

**Winner/Loser Logic**: Based on **predicted scores**

```python
# Simple comparison
if prediction.predicted_team1_score > prediction.predicted_team2_score:
    winner = team1
    loser = team2
elif prediction.predicted_team2_score > prediction.predicted_team1_score:
    winner = team2
    loser = team1
else:
    # Draw (in group stage, draw = 1 point each, no winner/loser)
    winner = None
    loser = None
```

**Example**:
| Prediction | Outcome | Winner | Points |
|-----------|---------|--------|--------|
| Brazil 2 - 0 Serbia | Brazil wins group | Brazil advances | 3 points (W=1, score exact=2) |
| France 1 - 1 Denmark | Draw | Both advance | 1 point each (correct outcome) |
| Germany 1 - 2 Costa Rica | Germany loses | Costa Rica advances | 0 points (incorrect outcome) |

### 3.2 Knockout Matches (Round of 16 onwards)

**Winner/Loser Logic**: More complex due to team placeholders

#### Problem: Teams aren't known until predictions are made

In knockout matches, teams come from two sources:
1. **Group Winners/Runners-up**: From group standings (e.g., "1A" = Group A winner)
2. **Match Winners**: From previous knockout matches (e.g., "W49" = Winner of Match 49)

#### Solution: `resolve_knockout_teams()` Function

This function determines which actual team will play in each knockout match:

```python
def resolve_knockout_teams(user_id: int, db: Session) -> Dict[str, Optional[Team]]:
    """
    Returns a mapping like:
    {
        "1A": Brazil,          # Group A winner
        "2H": Netherlands,     # Group H runner-up
        "W49": Argentina,      # Winner of match 49 (based on user's prediction)
        "L50": France,         # Loser of match 50 (based on user's prediction)
        ...
    }
    """
```

**Process**:
1. Calculate group standings from user's predictions
2. Get top 1 team from each group → "1A", "1B", ... "1H"
3. Get runner-up from each group → "2A", "2B", ... "2H"
4. For each knockout match in order:
   - Resolve the two teams playing (using placeholders)
   - Look at user's prediction for that match
   - Determine predicted winner → store as "W{match_number}"
   - Determine predicted loser → store as "L{match_number}"

**Example - Round of 16 Match 1 (Match 49)**

```
Match 49:
  team1_placeholder: "1A"  → resolves to Brazil
  team2_placeholder: "2B"  → resolves to England

User Prediction:
  predicted_team1_score: 1
  predicted_team2_score: 0
  → Brazil wins!

Resolution stored:
  "W49": Brazil   (winner advances to quarters)
  "L49": England  (loser is eliminated)
```

**Example - Semi-Final (Match 63)**

```
Match 63:
  team1_placeholder: "W61"  → resolves to Argentina (from previous match)
  team2_placeholder: "W62"  → resolves to France (from previous match)

User Prediction:
  predicted_team1_score: 3
  predicted_team2_score: 1
  → Argentina wins!

Resolution stored:
  "W63": Argentina  (advances to Final)
  "L63": France     (plays for 3rd place or is eliminated)
```

### 3.3 Handling Ties in Knockout

In knockout matches, ties require a penalty shootout:

```python
# If scores are tied
if prediction.predicted_team1_score == prediction.predicted_team2_score:
    # Check if user predicted a penalty winner
    if prediction.penalty_shootout_winner_id == team1_id:
        winner = team1
    elif prediction.penalty_shootout_winner_id == team2_id:
        winner = team2
    else:
        winner = None  # Prediction incomplete
```

---

## 4. Point System

### Overview

The game awards points for accurate predictions:

| Prediction Level | Group Stage | Knockout |
|------------------|-------------|----------|
| **Correct Outcome** | 1 point | 1 point × 2 = **2 points** |
| **Exact Score** | +2 points | +2 points × 2 = **+4 points** |
| **Total Max** | 3 points | **6 points** |

**Key Rule**: Knockout points are **doubled** (2x multiplier) and only awarded if predicted teams match actual teams.

### 4.1 Group Stage Scoring

**Function**: `calculate_match_points(prediction, match)`

```python
points = 0

# 1. Check if outcome is correct
if prediction.predicted_team1_score > prediction.predicted_team2_score:
    predicted_winner_id = team1_id
elif prediction.predicted_team2_score > prediction.predicted_team1_score:
    predicted_winner_id = team2_id
else:
    predicted_winner_id = None  # Draw

if predicted_winner_id == actual_winner_id:
    points += 1  # +1 for correct outcome

# 2. Check if score is exact
if (prediction.predicted_team1_score == match.actual_team1_score and
    prediction.predicted_team2_score == match.actual_team2_score):
    points += 2  # +2 for exact score

return points  # Can be 0, 1, or 3
```

**Example Table**:

| Prediction | Actual | Outcome | Score | Points |
|-----------|--------|---------|-------|--------|
| Spain 2-1 Germany | Spain 2-1 Germany | ✓ | ✓ | **3** (1+2) |
| Spain 2-1 Germany | Spain 1-0 Germany | ✓ | ✗ | **1** (outcome only) |
| Spain 2-1 Germany | Germany 1-0 Spain | ✗ | ✗ | **0** |
| Italy 1-1 Sweden | Italy 1-1 Sweden | ✓ | ✓ | **3** (draw + exact) |

### 4.2 Knockout Scoring

**Function**: `calculate_knockout_points(prediction, match, predicted_team1_id, predicted_team2_id)`

**Critical Requirement**: Predicted teams must **exactly match** actual teams playing in the match.

```python
predicted_ids = {predicted_team1_id, predicted_team2_id}
actual_ids = {match.team1_id, match.team2_id}

# Teams must match for any points
if predicted_ids != actual_ids:
    return {"points": 0, "status": "pending"}

# Teams match! Score with 2x multiplier
full = calculate_match_points(prediction, match)
full["points"] *= 2  # Double the points

return full
```

**Why the 2x multiplier?** Because in knockout, your path through the bracket depends entirely on your predictions. If you predicted the wrong teams to advance, you're in a different fantasy bracket path than reality.

**Example - Round of 16 (Match 49)**

**Scenario 1: Teams match, outcome correct, score exact**
```
Prediction: Brazil 2-1 Mexico
Actual:     Brazil 2-1 Mexico

Teams:     {Brazil, Mexico} == {Brazil, Mexico} ✓
Outcome:   Brazil wins both ✓
Score:     2-1 both ✓

Points: (1 + 2) × 2 = 6 points
```

**Scenario 2: Teams match, outcome correct, score wrong**
```
Prediction: Brazil 2-1 Mexico
Actual:     Brazil 1-0 Mexico

Teams:     {Brazil, Mexico} == {Brazil, Mexico} ✓
Outcome:   Brazil wins both ✓
Score:     2-1 vs 1-0 ✗

Points: 1 × 2 = 2 points
```

**Scenario 3: Teams DON'T match (prediction was wrong)**
```
Prediction: Brazil 2-1 Mexico  (for Round of 16 Match 1)
Actual:     Argentina 1-0 Saudi Arabia  (teams are different!)

Teams:     {Brazil, Mexico} != {Argentina, Saudi Arabia} ✗

Points: 0 (no points awarded, status: "pending")
Reason: Your bracket predicted different teams, so you're in an alternate universe
```

### 4.3 Total Score Calculation

**Function**: `calculate_total_user_score(user_id, db)`

Aggregates points from all matches:

```python
def calculate_total_user_score(user_id: int, db):
    total = 0
    
    # 1. Group stage: simple scoring
    for prediction, match in group_stage_matches:
        total += calculate_match_points(prediction, match)["points"]
    
    # 2. Knockout: resolve teams, then score
    for match in knockout_matches:
        team1, team2 = resolve_match_teams(match, user_id, db)
        prediction = predictions_dict[match.id]
        
        total += calculate_knockout_points(
            prediction, match,
            team1.id, team2.id
        )["points"]
    
    return total
```

**Maximum Possible Score**: 
- Group stage: 48 matches × 3 points = 144 points
- Knockout: 16 matches × 6 points = 96 points
- **Total: 240 points**

---

## 5. Practical Examples

### Example 1: User's Complete Group Stage

**Setup**: User is in Group A with Brazil vs Serbia

| Match | Prediction | Actual | Outcome Points | Score Points | Total |
|-------|-----------|--------|-----------------|--------------|-------|
| Brazil - Serbia | 3-0 | 3-0 | 1 | 2 | **3** |
| Brazil - Costa Rica | 2-0 | 2-1 | 1 | 0 | **1** |
| Brazil - Switzerland | 1-0 | 1-0 | 1 | 2 | **3** |

**Group Result**:
- Brazil finishes 1st (qualifies as "1A")
- User earned 7 points from Group A

### Example 2: User's Knockout Path

**Starting bracket predictions**:
```
Round of 16 (Match 49):
  1A (Brazil) vs 2B (England)
  User predicts: Brazil 1-0 → Brazil to Quarter-Finals

Quarters (Match 57):
  W49 (Brazil) vs W50 (France)
  User predicts: Brazil 0-2 → France to Semi-Finals

Semi-Final (Match 61):
  W57 (France) vs W58 (Germany)
  User predicts: France 2-1 → France to Final

Final (Match 63):
  W61 (France) vs W62 (Argentina)
  User predicts: France 1-1, France wins penalties → France Champion!
```

**Actual tournament results**:
```
Match 49 actual: Brazil 1-0 England ✓ (matches prediction, teams correct)
  Points: (1+2) × 2 = 6 points
  Resolution: W49 = Brazil, L49 = England

Match 57 actual: France 2-0 Netherlands (NOT Brazil!)
  Predicted teams: {Brazil, France}
  Actual teams:   {France, Netherlands}
  Teams don't match ✗
  Points: 0 (pending status)
  Resolution: W57 = France, L57 = Netherlands
```

Because the user predicted Brazil would beat France in quarters, but France actually beat Netherlands, their bracket diverged from reality. No more points can be earned from their knockouts (all future matches have wrong teams).

### Example 3: Database State at Match 49

**Tables after user predicts and Match 49 finishes**:

```sql
-- User's prediction
SELECT * FROM predictions WHERE user_id=5 AND match_id=49;
┌────┬─────────┬──────────┬──────────────────┬──────────────────┬───────────────────┐
│ id │ user_id │ match_id │ predicted_team1  │ predicted_team2  │ predicted_winner  │
├────┼─────────┼──────────┼──────────────────┼──────────────────┼───────────────────┤
│ 1  │    5    │    49    │        1         │        2         │        1          │
└────┴─────────┴──────────┴──────────────────┴──────────────────┴───────────────────┘

-- Match result stored
SELECT * FROM matches WHERE id=49;
┌────┬────────────────────┬──────────────┬──────────┬──────────┬──────────────────┬──────────────────┬────────────┐
│ id │ round              │ match_number │ team1_id │ team2_id │ actual_team1_score│ actual_team2_score│ is_finished│
├────┼────────────────────┼──────────────┼──────────┼──────────┼──────────────────┼──────────────────┼────────────┤
│ 49 │ Round of 16        │     49       │    1     │    2     │        1         │        0         │    true    │
└────┴────────────────────┴──────────────┴──────────┴──────────┴──────────────────┴──────────────────┴────────────┘

-- Teams referenced
SELECT id, name FROM teams WHERE id IN (1, 2);
┌────┬─────────┐
│ id │ name    │
├────┼─────────┤
│  1 │ Brazil  │
│  2 │ England │
└────┴─────────┘
```

**Scoring calculation**:
```python
calculate_match_points(prediction, match) returns:
{
    "points": 3,
    "breakdown": ["Correct Outcome (+1)", "Exact Score (+2)"],
    "status": "complete"
}

calculate_knockout_points(prediction, match, 1, 2) returns:
{
    "points": 6,  # (1+2) × 2
    "breakdown": ["Correct Outcome (+1) x2", "Exact Score (+2) x2"],
    "status": "complete"
}
```

---

## 6. Bracket Views & Scoring Integration

### 6.1 Bracket View (`/bracket/view`)

Shows all group stage predictions with scoring:

```
Group Stage Results:
├── Brazil 3-0 Serbia
│   Prediction: 3-0 ✓ | Points: 3 [Correct Outcome +1, Exact Score +2]
├── Brazil 2-1 Costa Rica
│   Prediction: 2-0 ✗ | Points: 1 [Correct Outcome +1]
└── ...

Total Group Points: 45

Knockout Matches:
├── Round of 16 - Match 49
│   Predicted: Brazil vs England
│   Actual:    Brazil vs England
│   Prediction: Brazil 1-0 ✓ | Points: 6 [Correct Outcome +1 x2, Exact Score +2 x2]
├── Quarter-Finals - Match 57
│   Predicted: Brazil vs France
│   Actual:    France vs Netherlands ✗
│   Prediction: Brazil 0-2 | Points: 0 [Teams don't match]
└── ...

Total Score: 51 points
```

### 6.2 Knockout Bracket View (`/bracket/knockout`)

Visual bracket tree showing:
- User's predicted teams and results
- Actual results (if available)
- Points earned per match
- Tournament champion (predicted or actual)

```
Round of 16                 Quarter-Finals            Semi-Finals
    |                            |                        |
 Brazil─┐                        |                        |
        ├──→ Brazil 1-0 ──→ Brazil─┐                      |
England─┘                        ├──→ Brazil 0-2 ──→ France─┐
                               France─┘                     ├──→ France
                                                        Germany─┘
France──┐
        ├──→ France 2-0 ─→ France─┐
Germany─┘                        ├──→ France 3-1 ─→ France (Champion)
                               Argentina─┘
```

---

## 7. Summary Table: Data Flow

| Component | Purpose | Key Tables | Example |
|-----------|---------|-----------|---------|
| **User Input** | Make predictions | predictions | "Brazil 2 vs 1 Serbia" |
| **Match Results** | Real tournament outcome | matches | "Brazil actually beat Serbia 2-1" |
| **Group Standings** | Calculate qualifiers | calculate_group_standings() | "Brazil 1st, Serbia 3rd in Group A" |
| **Knockout Resolution** | Determine bracket path | resolve_knockout_teams() | "1A vs 2B = Brazil vs England" |
| **Scoring** | Calculate points | calculate_match_points() | User earned 3 points for that match |
| **Bracket View** | Display user's path | bracket_view() | Show all predictions + points |

---

## 8. Key Design Patterns

### 8.1 Placeholder Resolution
- **Problem**: Knockout teams unknown until earlier rounds finish
- **Solution**: Use placeholders ("1A", "2B", "W49") and resolve at display time
- **Benefit**: User can make full bracket predictions before tournament starts

### 8.2 Two-Phase Prediction
1. **User makes prediction**: Scores AND explicit winner (handles ties/penalties)
2. **System evaluates**: Compares user's logic to actual results

### 8.3 Fantasy Bracket
- Each user's bracket is independent
- User's predictions determine their path (W49 = their predicted winner)
- Scoring only if predicted teams match actual teams

### 8.4 Doubled Knockout Points
- Group stage: mistakes only lose you 1-3 points per match
- Knockout: mistakes cost you entire branch (0 points)
- Makes knockout predictions more strategic

---

## 9. Testing & Debugging

### Checking User's Score

```python
from app.scoring import calculate_total_user_score
from app.database import SessionLocal

db = SessionLocal()
user_id = 5
total = calculate_total_user_score(user_id, db)
print(f"User {user_id} has {total} points")
```

### Checking Group Standings

```python
from app.standings import calculate_group_standings

standings = calculate_group_standings(user_id, db)
for group, teams in standings.items():
    print(f"Group {group}:")
    for team_standing in teams:
        print(f"  {team_standing.team.name}: {team_standing.points}pts")
```

### Checking Knockout Resolution

```python
from app.knockout import resolve_knockout_teams

resolution = resolve_knockout_teams(user_id, db)
print(resolution)
# Output: {'1A': Team(Brazil), '2B': Team(England), 'W49': Team(Brazil), ...}
```

---

## 10. Common Scenarios

### Scenario 1: User gets perfect score on group stage
- Predicts all 48 matches exactly
- Earns 3 points per match = **144 points**

### Scenario 2: User's bracket diverges early
- Predicts Brazil beats France in Round of 16
- Actually, France beats Netherlands (Brazil doesn't play them)
- All user's subsequent predictions for that branch earn 0 points
- User can only score on other bracket branches

### Scenario 3: User correctly predicts champion
- Predicts France wins tournament
- Gets 6 points from Final match
- Total Final contribution: 6 points (or 0 if they got teams wrong)

---

## Quick Reference

**Max Points Per Match**:
- Group Stage: 3 points (1 for outcome, 2 for exact score)
- Knockout: 6 points (2 for outcome, 4 for exact score)

**Total Tournament Max**: 240 points

**Key Files**:
- `app/models.py` - Database schemas
- `app/scoring.py` - Point calculation logic
- `app/knockout.py` - Team placeholder resolution
- `app/standings.py` - Group standings calculation
- `app/routers/brackets.py` - Bracket views & API

**Key Functions**:
- `calculate_match_points()` - Group stage scoring
- `calculate_knockout_points()` - Knockout scoring
- `resolve_knockout_teams()` - Determine bracket path
- `calculate_total_user_score()` - Total user points
- `calculate_group_standings()` - Group standings from predictions
