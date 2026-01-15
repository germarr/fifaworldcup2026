
  Plan Summary

  Database Design (9 tables)

  - Core: users, sessions, fifa_teams, stadiums, matches (104), predictions
  - Third-place: user_third_place_rankings (for manual drag-drop ordering)
  - Competition: competition_teams, team_memberships

  Key Design Decisions

  1. Efficient predictions: One row per user per match with UNIQUE(user_id, match_id)
  2. Flexible teams: group_letter nullable to handle TBD team assignments
  3. Bracket slots: home_slot/away_slot fields enable dynamic bracket population
  4. Score tracking: points_earned stored per prediction for fast leaderboard queries

  10 Implementation Phases

  1. Project Foundation (structure, database, TailwindCSS)
  2. Authentication (register, login, 30-day sessions, cookie consent)
  3. Admin Panel (teams, matches, live scores, users)
  4. Data Seeding Scripts
  5. Group Stage Predictions
  6. Third-Place Ranking (drag-drop interface)
  7. Knockout Bracket (progressive building)
  8. Scoring System
  9. Leaderboard
  10. Competition Teams (create, join, compare)

  Scoring

  - Group: 1pt correct outcome, 3pt exact score
  - Knockout: 2pt correct winner, 3pt exact score

────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 Ready to code?

 Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 FIFA World Cup 2026 Bracket Game - Implementation Plan

 Project Overview

 A bracket prediction game for the FIFA World Cup 2026 where users predict match outcomes, build their brackets progressively, and
 compete with friends in teams.

 Tech Stack: FastAPI + Jinja2 + TailwindCSS + SQLite (via SQLModel)

 ---
 Database Schema

 Core Tables

 1. users

 - id: INTEGER PRIMARY KEY
 - email: TEXT UNIQUE NOT NULL
 - password_hash: TEXT NOT NULL
 - display_name: TEXT NOT NULL
 - is_admin: BOOLEAN DEFAULT FALSE
 - cookie_consent: BOOLEAN DEFAULT FALSE
 - created_at: DATETIME
 - updated_at: DATETIME

 2. sessions

 - id: INTEGER PRIMARY KEY
 - user_id: INTEGER FK -> users
 - session_token: TEXT UNIQUE NOT NULL
 - expires_at: DATETIME NOT NULL (30 days from creation)
 - created_at: DATETIME

 3. fifa_teams (48 World Cup national teams)

 - id: INTEGER PRIMARY KEY
 - name: TEXT NOT NULL
 - country_code: TEXT (ISO 3166-1 alpha-3, e.g., "BRA", "ARG")
 - flag_emoji: TEXT
 - group_letter: TEXT (A-L, nullable until assigned)
 - created_at: DATETIME
 - updated_at: DATETIME

 4. stadiums

 - id: INTEGER PRIMARY KEY
 - name: TEXT NOT NULL
 - city: TEXT NOT NULL
 - country: TEXT NOT NULL

 5. matches (104 total matches)

 - id: INTEGER PRIMARY KEY
 - match_number: INTEGER UNIQUE (1-104)
 - round: TEXT NOT NULL (group_stage, round_of_32, round_of_16, quarter_final, semi_final, third_place, final)
 - group_letter: TEXT (nullable, for group stage only)
 - home_team_id: INTEGER FK -> fifa_teams (nullable for future knockout)
 - away_team_id: INTEGER FK -> fifa_teams (nullable for future knockout)
 - home_slot: TEXT (bracket position, e.g., "1A", "2B", "3rd_1")
 - away_slot: TEXT
 - stadium_id: INTEGER FK -> stadiums
 - scheduled_datetime: DATETIME NOT NULL
 - actual_home_score: INTEGER (nullable)
 - actual_away_score: INTEGER (nullable)
 - actual_winner_team_id: INTEGER FK (for knockout - who advanced)
 - status: TEXT DEFAULT 'scheduled' (scheduled, in_progress, completed)
 - created_at: DATETIME
 - updated_at: DATETIME

 6. predictions

 - id: INTEGER PRIMARY KEY
 - user_id: INTEGER FK -> users
 - match_id: INTEGER FK -> matches
 - predicted_outcome: TEXT (home_win, away_win, draw)
 - predicted_winner_team_id: INTEGER FK -> fifa_teams (for knockout)
 - predicted_home_score: INTEGER (nullable)
 - predicted_away_score: INTEGER (nullable)
 - points_earned: INTEGER DEFAULT 0
 - created_at: DATETIME
 - updated_at: DATETIME
 - UNIQUE(user_id, match_id)

 7. user_third_place_rankings

 - id: INTEGER PRIMARY KEY
 - user_id: INTEGER FK -> users
 - team_id: INTEGER FK -> fifa_teams
 - rank_position: INTEGER (1-12, where 1-8 qualify)
 - created_at: DATETIME
 - updated_at: DATETIME
 - UNIQUE(user_id, team_id)
 - UNIQUE(user_id, rank_position)

 Team Competition Tables

 8. competition_teams (user-created teams for competing)

 - id: INTEGER PRIMARY KEY
 - name: TEXT NOT NULL
 - admin_user_id: INTEGER FK -> users
 - created_at: DATETIME

 9. team_memberships

 - id: INTEGER PRIMARY KEY
 - team_id: INTEGER FK -> competition_teams
 - user_id: INTEGER FK -> users
 - joined_at: DATETIME
 - UNIQUE(team_id, user_id)

 ---
 Project Structure

 fifaworldcup2026V2/
 ├── main.py                      # FastAPI app entry point
 ├── app/
 │   ├── __init__.py
 │   ├── config.py                # Settings (SECRET_KEY, DB path, etc.)
 │   ├── database.py              # SQLite/SQLModel setup
 │   ├── models/                  # SQLModel models
 │   │   ├── __init__.py
 │   │   ├── user.py
 │   │   ├── session.py
 │   │   ├── fifa_team.py
 │   │   ├── stadium.py
 │   │   ├── match.py
 │   │   ├── prediction.py
 │   │   └── competition_team.py
 │   ├── schemas/                 # Pydantic schemas for API
 │   │   ├── __init__.py
 │   │   ├── user.py
 │   │   ├── match.py
 │   │   └── prediction.py
 │   ├── routers/                 # API routes
 │   │   ├── __init__.py
 │   │   ├── auth.py              # Login, register, logout, cookie consent
 │   │   ├── pages.py             # HTML page routes
 │   │   ├── matches.py           # Match data API
 │   │   ├── predictions.py       # User predictions API
 │   │   ├── leaderboard.py       # Leaderboard API
 │   │   ├── teams.py             # Competition teams API
 │   │   └── admin.py             # Admin panel routes
 │   ├── services/                # Business logic
 │   │   ├── __init__.py
 │   │   ├── auth.py              # Password hashing, session management
 │   │   ├── scoring.py           # Points calculation
 │   │   ├── bracket.py           # Bracket progression logic
 │   │   └── standings.py         # Group standings calculation
 │   ├── dependencies.py          # FastAPI dependencies (get_current_user, etc.)
 │   ├── templates/               # Jinja2 templates
 │   │   ├── base.html            # Base layout with TailwindCSS
 │   │   ├── components/          # Reusable components
 │   │   │   ├── navbar.html
 │   │   │   ├── match_card.html
 │   │   │   └── team_flag.html
 │   │   ├── index.html           # Homepage
 │   │   ├── auth/
 │   │   │   ├── login.html
 │   │   │   ├── register.html
 │   │   │   └── cookie_consent.html
 │   │   ├── bracket/
 │   │   │   ├── groups.html      # Group stage predictions
 │   │   │   ├── third_place.html # Third-place ranking (drag-drop)
 │   │   │   ├── knockout.html    # Knockout bracket view
 │   │   │   └── match_detail.html
 │   │   ├── leaderboard/
 │   │   │   ├── global.html      # Global leaderboard
 │   │   │   └── team_compare.html
 │   │   ├── teams/
 │   │   │   ├── list.html        # User's teams
 │   │   │   ├── detail.html      # Team members & scores
 │   │   │   ├── create.html
 │   │   │   └── manage.html      # Admin manage members
 │   │   └── admin/
 │   │       ├── dashboard.html
 │   │       ├── teams.html       # Manage FIFA teams
 │   │       ├── matches.html     # Input live scores
 │   │       └── users.html       # View users
 │   └── static/
 │       ├── css/
 │       │   └── output.css       # TailwindCSS compiled
 │       └── js/
 │           ├── app.js           # Main JS
 │           └── drag-drop.js     # Third-place ranking
 ├── scripts/
 │   ├── seed_teams.py            # Seed 48 FIFA teams
 │   ├── seed_stadiums.py         # Seed stadiums
 │   ├── seed_matches.py          # Seed 104 match schedule
 │   └── seed_players.py          # Seed test users with random predictions
 ├── tailwind.config.js
 ├── package.json
 ├── pyproject.toml
 └── worldcup.db                  # SQLite database file

 ---
 Implementation Phases

 Phase 1: Project Foundation

 1. Set up project structure (folders, __init__.py files)
 2. Configure FastAPI app with Jinja2 templates
 3. Set up TailwindCSS build pipeline
 4. Create SQLModel database models
 5. Initialize SQLite database with all tables
 6. Create base HTML template with TailwindCSS

 Phase 2: Authentication System

 1. User registration (email, password, display name)
 2. Password hashing with bcrypt
 3. Login/logout functionality
 4. Session management with 30-day cookies
 5. Cookie consent banner and storage
 6. get_current_user dependency for protected routes

 Phase 3: Admin Panel

 1. Admin authentication (admin/password hardcoded for now)
 2. FIFA teams management (CRUD)
 3. Stadiums management
 4. Matches management (add/edit with dates, teams, stadiums)
 5. Live score input interface
 6. User list view

 Phase 4: Data Seeding Scripts

 1. Seed 48 FIFA teams (with placeholders for TBD teams)
 2. Seed stadiums (USA, Mexico, Canada venues)
 3. Seed 104 matches with schedule structure
 4. Seed test users with random predictions

 Phase 5: Group Stage Predictions

 1. Display all 12 groups with 4 teams each
 2. Match cards showing home vs away teams
 3. Prediction UI: select outcome (W/L/D)
 4. Optional score prediction
 5. Auto-generate random scores if user skips
 6. Lock predictions when match starts
 7. Real-time group standings calculation

 Phase 6: Third-Place Ranking

 1. Calculate third-place teams from user's predictions
 2. Display standings using tiebreaker rules:
   - Points > Goal Diff > Goals Scored
 3. Drag-and-drop interface for manual reordering
 4. Save user's third-place ranking

 Phase 7: Knockout Bracket

 1. Generate Round of 32 bracket from group predictions
 2. Populate with user's predicted qualifiers
 3. Prediction UI for each knockout match
 4. Progressive bracket building (R32 -> R16 -> QF -> SF -> Final)
 5. Third-place match prediction
 6. Visual bracket display

 Phase 8: Scoring System

 1. Calculate points after admin inputs results:
   - Group stage: 1pt outcome, 3pt exact score
   - Knockout: 2pt correct winner, 3pt exact score
 2. Update points_earned in predictions table
 3. Calculate user total scores

 Phase 9: Leaderboard

 1. Global leaderboard sorted by total points
 2. Show user rank, display name, points
 3. Pagination for large user lists

 Phase 10: Competition Teams

 1. Create team (any user can create)
 2. Team admin can add/remove members
 3. Join team (via invite or search)
 4. Leave team
 5. Team detail page with members and aggregate score
 6. Team comparison filter (select 2 teams to compare)
 7. Min 2 members validation

 ---
 Scoring Logic

 def calculate_points(prediction, actual_match):
     points = 0
     is_knockout = actual_match.round != 'group_stage'

     # Determine actual outcome
     if actual_match.actual_home_score > actual_match.actual_away_score:
         actual_outcome = 'home_win'
     elif actual_match.actual_home_score < actual_match.actual_away_score:
         actual_outcome = 'away_win'
     else:
         actual_outcome = 'draw'

     # Check outcome prediction
     outcome_correct = prediction.predicted_outcome == actual_outcome

     # For knockout, also check winner team
     if is_knockout:
         winner_correct = prediction.predicted_winner_team_id == actual_match.actual_winner_team_id
         if winner_correct:
             points = 2  # Correct knockout winner
     else:
         if outcome_correct:
             points = 1  # Correct group stage outcome

     # Exact score bonus (replaces base points)
     if (prediction.predicted_home_score == actual_match.actual_home_score and
         prediction.predicted_away_score == actual_match.actual_away_score):
         points = 3  # Exact score in any round

     return points

 ---
 Group Standings Calculation

 def calculate_group_standings(user_predictions, group_letter):
     """
     From user's predictions, calculate standings for a group.
     Returns list of teams sorted by: Points > Goal Diff > Goals Scored
     """
     teams_stats = {}  # team_id -> {points, gf, ga, gd}

     for pred in user_predictions:
         match = pred.match
         if match.group_letter != group_letter:
             continue

         home_score = pred.predicted_home_score
         away_score = pred.predicted_away_score

         # Update stats for both teams
         # ... calculate points, goals for/against

     # Sort by points, then goal diff, then goals scored
     return sorted(teams_stats, key=lambda t: (t.points, t.gd, t.gf), reverse=True)

 ---
 Third-Place Qualification Logic

 For 2026 World Cup with 48 teams:
 - 12 groups x 4 teams = 48 teams
 - Top 2 from each group (24 teams) + 8 best third-place teams = 32 teams for knockout
 - Rank all 12 third-place teams, top 8 qualify

 User flow:
 1. System calculates third-place standings from predictions
 2. User sees ranked list with stats
 3. User can drag-drop to manually reorder
 4. Top 8 in user's ranking advance to their R32 bracket

 ---
 Key API Endpoints

 Auth

 - POST /auth/register - Create account
 - POST /auth/login - Login, set session cookie
 - POST /auth/logout - Clear session
 - POST /auth/cookie-consent - Accept cookies

 Predictions

 - GET /predictions/groups - Get user's group predictions
 - POST /predictions/match/{id} - Submit/update prediction
 - GET /predictions/standings/{group} - Get calculated standings
 - GET /predictions/third-place - Get third-place ranking
 - POST /predictions/third-place - Save manual ranking
 - GET /predictions/bracket - Get knockout bracket

 Leaderboard

 - GET /leaderboard - Global rankings
 - GET /leaderboard/team/{id} - Team rankings

 Teams

 - GET /teams - List user's teams
 - POST /teams - Create team
 - GET /teams/{id} - Team detail
 - POST /teams/{id}/join - Join team
 - POST /teams/{id}/leave - Leave team
 - POST /teams/{id}/members - Add member (admin)
 - DELETE /teams/{id}/members/{user_id} - Remove member (admin)
 - GET /teams/compare?team1={id}&team2={id} - Compare two teams

 Admin

 - GET /admin/ - Dashboard
 - GET /admin/teams - Manage FIFA teams
 - POST /admin/teams - Add team
 - PUT /admin/teams/{id} - Edit team
 - DELETE /admin/teams/{id} - Delete team
 - GET /admin/matches - Manage matches
 - PUT /admin/matches/{id}/score - Input live score
 - GET /admin/users - View all users

 ---
 Verification Plan

 1. Database: Run seed scripts, verify all tables created with correct relationships
 2. Auth Flow: Register -> Login -> Session persists -> Logout -> Session cleared
 3. Admin Panel: Login as admin, add/edit teams, input match scores
 4. Predictions: Make group predictions, verify standings calculate correctly
 5. Third-Place: Verify drag-drop saves ranking, top 8 populate knockout
 6. Knockout: Verify bracket populates from predictions, can predict winners
 7. Scoring: Input real results via admin, verify points calculate correctly
 8. Leaderboard: Verify rankings update, users sorted by points
 9. Teams: Create team, add members, verify aggregate scores
 10. Deadlines: Verify predictions lock after match starts

 ---
 Files to Create/Modify

 New Files (in order of creation)

 1. app/__init__.py
 2. app/config.py
 3. app/database.py
 4. app/models/*.py (all model files)
 5. app/schemas/*.py
 6. app/services/*.py
 7. app/dependencies.py
 8. app/routers/*.py
 9. app/templates/**/*.html
 10. app/static/js/*.js
 11. scripts/*.py
 12. package.json and tailwind.config.js
 13. Update main.py

 Estimated File Count

 - ~15 Python modules
 - ~20 HTML templates
 - ~3 JS files
 - ~4 seed scripts
 - ~3 config files
