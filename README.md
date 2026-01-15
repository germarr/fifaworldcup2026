# ⚽🌍 FIFA WORLD CUP 2026 BRACKET PREDICTION GAME 🎮🏆

> **A HIGH-OCTANE, COMPETITIVE BRACKET PREDICTION PLATFORM** for the FIFA World Cup 2026 where you predict match outcomes, build knockout brackets, and crush the competition!

---

## 🚀 WHAT IS THIS?

This is a **FULL-STACK WEB APPLICATION** designed to make FIFA World Cup 2026 predictions EPIC! 

Create an account → Make predictions on all 104 matches → Build your bracket progressively → Compete with friends in teams → Dominate the global leaderboard! 

**Business Logic**: Earn points for correct predictions (1pt for group outcomes, 3pts for exact scores, 2pts for knockout winners), rank third-place teams using drag-and-drop, and watch your score skyrocket as results roll in!

---

## 💪 TECH STACK - BATTLE-TESTED & POWERFUL

### 🐍 **Backend: Python + FastAPI**
- **FastAPI** (v0.128.0) - Modern async web framework, lightning-fast, with automatic API documentation
- **Uvicorn** (v0.40.0) - ASGI server for running the application

### 🗄️ **Database: SQLite via SQLModel**
- **SQLModel** (v0.0.31) - Seamless SQL database ORM with Pydantic validation
- **SQLite** (worldcup.db) - Lightweight, file-based relational database
- **DuckDB** (v1.4.3) - Optional analytical database for advanced queries

### 🎨 **Frontend: Jinja2 Templates + TailwindCSS**
- **Jinja2** (v3.1.6) - Powerful template engine for dynamic HTML rendering
- **TailwindCSS** (v3.4.0) - Utility-first CSS framework for stunning responsive UI
- **Alpine.js** (via TailwindCSS) - Lightweight JavaScript framework for interactivity

### 🔐 **Security & Utils**
- **bcrypt** (v5.0.0) - Industry-standard password hashing
- **python-multipart** (v0.0.21) - Form data parsing
- **httpx** (v0.28.1) - Async HTTP client
- **Requests** (v2.32.5) - HTTP requests library

### 📊 **Data Processing**
- **Pandas** (v2.3.3) - Data manipulation and analysis
- **NumPy** (v2.4.0) - Numerical computing

### 🧪 **Testing**
- **pytest** (v9.0.2) - Testing framework

---

## 🏗️ DATABASE ARCHITECTURE - 9 TABLES OF GLORY

### **Core Tables**

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **users** | Player accounts | email, password_hash, display_name, is_admin, cookie_consent |
| **sessions** | Login sessions (30-day expiry) | user_id, session_token, expires_at |
| **fifa_teams** | 48 World Cup national teams | name, country_code, flag_emoji, group_letter (A-L) |
| **stadiums** | Venues across USA/Mexico/Canada | name, city, country |
| **matches** | 104 total tournament matches | match_number, round, home/away_team_id, scores, status, bracket_slots |
| **predictions** | User match predictions (UNIQUE per user/match) | user_id, match_id, predicted_outcome, scores, points_earned |

### **Advanced Tables**

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **user_third_place_rankings** | Manual drag-drop ranking of 12 third-place teams | user_id, team_id, rank_position (1-12, top 8 advance) |
| **competition_teams** | User-created competitive teams | name, admin_user_id |
| **team_memberships** | Users joining competition teams | team_id, user_id |

**Key Design Features:**
- ✅ **One prediction per user per match** - UNIQUE constraint ensures no duplicates
- ✅ **Dynamic bracket slots** - home_slot/away_slot for progressive knockout building
- ✅ **Nullable teams** - Handles TBD team assignments in early tournament phases
- ✅ **Instant scoring** - points_earned stored per prediction for blazing-fast leaderboard queries

---

## 📁 PROJECT STRUCTURE - ORGANIZED CHAOS

```
fifaworldcup2026V2/
├── main.py                          # ⚡ FastAPI app entry point
├── app/
│   ├── config.py                    # 🔧 Settings & environment
│   ├── database.py                  # 🗄️ SQLModel + SQLite setup
│   ├── dependencies.py              # 🔐 FastAPI dependencies (auth, etc)
│   ├── models/                      # 📊 Database ORM models
│   │   ├── user.py, session.py, fifa_team.py, stadium.py
│   │   ├── match.py, prediction.py, competition_team.py
│   │   └── third_place_ranking.py
│   ├── schemas/                     # 🔀 Pydantic request/response schemas
│   │   └── (Validation schemas for API)
│   ├── services/                    # 💼 Business logic
│   │   ├── auth.py                  # Password hashing, session management
│   │   ├── scoring.py               # POINTS CALCULATION ENGINE 🎯
│   │   ├── bracket.py               # Bracket progression & qualification logic
│   │   └── standings.py             # Group standings calculation
│   ├── routers/                     # 🛣️ API endpoints
│   │   ├── auth.py                  # Register, login, logout, cookies
│   │   ├── pages.py                 # HTML page routes
│   │   ├── predictions.py           # Submit/retrieve predictions
│   │   ├── leaderboard.py           # Rankings & scores
│   │   ├── bracket.py               # Knockout bracket view
│   │   ├── teams.py                 # Competition team management
│   │   └── admin.py                 # Admin panel for data entry
│   ├── templates/                   # 🎨 Jinja2 HTML templates
│   │   ├── base.html                # Master layout
│   │   ├── index.html, auth/, bracket/, teams/, leaderboard/, admin/
│   │   └── components/              # Reusable navbar, cards, etc
│   └── static/
│       ├── css/output.css           # 🎨 Compiled TailwindCSS
│       └── js/app.js                # 🎯 Client-side interactivity
├── scripts/                         # 📝 Data seeding scripts
│   ├── seed_teams.py                # Load 48 FIFA teams
│   ├── seed_stadiums.py             # Load venues
│   ├── seed_matches.py              # Generate 104-match schedule
│   └── seed_players.py              # Create test users with predictions
├── package.json, tailwind.config.js # 🎨 Frontend tooling
├── pyproject.toml                   # 📦 Python dependencies (via uv)
└── worldcup.db                      # 🗄️ SQLite database file

```

---

## 💰 BUSINESS LOGIC - THE SCORING SYSTEM

### **How You Earn Points:**

**GROUP STAGE (Most Intense)**
- ✅ **Correct Outcome** → 1 point (W/D/L prediction correct)
- 🎯 **Exact Score** → 3 points (Bonus, replaces outcome points)

**KNOCKOUT ROUNDS (High Stakes)**
- ⭐ **Correct Winner** → 2 points (Picked right advancing team)
- 🎯 **Exact Score** → 3 points (Bonus, replaces winner points)

**THIRD-PLACE QUALIFICATION**
- 🏆 48 teams → 12 groups (top 2 auto-qualify = 24 teams)
- 🎰 8 best third-place teams also advance
- **User's task**: Drag-drop rank all 12 third-place contenders → System uses top 8 for their bracket

### **Example Scoring Journey**
```
🇧🇷 Brazil vs 🇸🇪 Sweden (Group Stage)
  You predict: Brazil wins 2-1 ❌ (Actual: Brazil 3-1)
  Points: 1 (Correct outcome: Brazil win)

🇦🇷 Argentina vs 🇫🇷 France (Final)
  You predict: Argentina 3-2 ✅ (Actual: Argentina 3-2)
  Points: 3 (EXACT SCORE!)

💪 Your match total: 4 points earned!
```

---

## 🎮 CORE FEATURES - WHAT YOU CAN DO

### 🔐 **Authentication**
- Register with email/password
- Login with 30-day session cookies
- Admin role for data entry
- Cookie consent tracking

### 🏟️ **Group Stage Predictions**
- View all 12 groups with 4 teams each
- Predict outcomes for all group stage matches
- Optional score predictions
- Real-time group standings calculation (points → goal diff → goals scored)
- Predictions lock when match starts

### 🏆 **Third-Place Ranking**
- System auto-calculates third-place standings
- **DRAG & DROP** interface to manually reorder 12 teams
- Save your ranking → Top 8 advance to your knockout bracket
- Uses tiebreaker rules: Points > Goal Difference > Goals Scored

### 🎯 **Knockout Bracket**
- Progressive bracket building (R32 → R16 → QF → SF → Final)
- Bracket populates with YOUR predicted qualifiers
- Predict winners for each knockout match
- Optional score predictions
- Visual bracket display

### 📊 **Leaderboard**
- Global rankings sorted by total points
- Rank, display name, points earned
- Pagination for thousands of users

### 👥 **Competition Teams**
- Create a team and invite friends
- Add/remove members (team admin only)
- Aggregate team scores
- Team detail pages with member rankings
- Compare two teams side-by-side

### 🛠️ **Admin Panel**
- Manage FIFA teams (create/edit/delete)
- Input live match scores
- View all users
- Dashboard with system overview

---

## 🔑 KEY API ENDPOINTS

### 🔐 **Auth Routes**
```
POST   /auth/register           - Create account
POST   /auth/login              - Login, set session cookie  
POST   /auth/logout             - Clear session
POST   /auth/cookie-consent     - Accept cookies
```

### 🎯 **Prediction Routes**
```
GET    /predictions/groups      - Fetch user's group predictions
POST   /predictions/match/{id}  - Submit/update prediction
GET    /predictions/standings/{group} - Calculated group standings
GET    /predictions/third-place - Fetch third-place ranking
POST   /predictions/third-place - Save manual ranking
GET    /predictions/bracket     - Fetch knockout bracket
```

### 🏆 **Leaderboard Routes**
```
GET    /leaderboard             - Global rankings
GET    /leaderboard/team/{id}   - Team rankings
```

### 👥 **Team Routes**
```
GET    /teams                   - List user's teams
POST   /teams                   - Create team
GET    /teams/{id}              - Team detail
POST   /teams/{id}/join         - Join team
POST   /teams/{id}/leave        - Leave team
POST   /teams/{id}/members      - Add member (admin)
DELETE /teams/{id}/members/{uid}- Remove member (admin)
GET    /teams/compare           - Compare two teams
```

### 🛠️ **Admin Routes**
```
GET    /admin/                  - Dashboard
GET    /admin/teams             - Manage FIFA teams
POST   /admin/teams             - Add team
PUT    /admin/teams/{id}        - Edit team
DELETE /admin/teams/{id}        - Delete team
GET    /admin/matches           - Manage matches
PUT    /admin/matches/{id}/score- Input live score
GET    /admin/users             - View all users
```

---

## 🚀 GET STARTED

### **1️⃣ Install Dependencies**
```bash
# Backend (Python with uv)
uv sync

# Frontend (TailwindCSS)
npm install
```

### **2️⃣ Build CSS**
```bash
npm run build:css        # One-time build
npm run watch:css        # Watch mode during development
```

### **3️⃣ Seed Database**
```bash
python scripts/seed_teams.py       # Load 48 FIFA teams
python scripts/seed_stadiums.py    # Load venues
python scripts/seed_matches.py     # Generate 104-match schedule
python scripts/seed_players.py     # Create test users
```

### **4️⃣ Run Application**
```bash
python main.py
# Server runs on http://localhost:8000
```

### **5️⃣ Access the App**
- 🌐 **Homepage**: http://localhost:8000/
- 🔐 **Register/Login**: http://localhost:8000/auth/register
- 🎯 **Bracket**: http://localhost:8000/bracket/groups
- 🏆 **Leaderboard**: http://localhost:8000/leaderboard
- 🛠️ **Admin**: http://localhost:8000/admin/ (requires admin access)

---

## 📊 DATABASE SCHEMA AT A GLANCE

```
USERS (Accounts & Auth)
├─ user_id, email, password_hash, display_name, is_admin, cookie_consent

SESSIONS (Login State)
├─ session_id, user_id → USERS, session_token, expires_at (30 days)

FIFA_TEAMS (National Teams)
├─ team_id, name, country_code, flag_emoji, group_letter (A-L)

STADIUMS (Venues)
├─ stadium_id, name, city, country

MATCHES (104 Tournament Matches)
├─ match_id, match_number (1-104), round, group_letter
├─ home_team_id → FIFA_TEAMS, away_team_id → FIFA_TEAMS
├─ home_slot, away_slot (bracket positions)
├─ stadium_id → STADIUMS, scheduled_datetime
├─ actual_home_score, actual_away_score, status (scheduled/in_progress/completed)

PREDICTIONS (User Guesses)
├─ prediction_id, user_id → USERS, match_id → MATCHES
├─ predicted_outcome (home_win/away_win/draw)
├─ predicted_home_score, predicted_away_score
├─ points_earned (auto-calculated)
├─ UNIQUE(user_id, match_id) ← Only 1 prediction per user per match!

USER_THIRD_PLACE_RANKINGS (Manual Ranking)
├─ ranking_id, user_id → USERS, team_id → FIFA_TEAMS
├─ rank_position (1-12, top 8 advance)
├─ UNIQUE(user_id, team_id), UNIQUE(user_id, rank_position)

COMPETITION_TEAMS (User-Created Teams)
├─ team_id, name, admin_user_id → USERS

TEAM_MEMBERSHIPS (Team Roster)
├─ membership_id, team_id → COMPETITION_TEAMS, user_id → USERS
├─ UNIQUE(team_id, user_id)
```

---

## 🎯 PROJECT TIMELINE - 10 IMPLEMENTATION PHASES

1. ✅ **Foundation** - Project structure, database, TailwindCSS setup
2. ✅ **Authentication** - Register, login, sessions, cookies
3. ✅ **Admin Panel** - Team/match/user management, live scores
4. ✅ **Data Seeding** - Load 48 teams, stadiums, 104 matches, test users
5. 🔄 **Group Predictions** - Match cards, outcome prediction, standings
6. 🔄 **Third-Place Ranking** - Drag-drop UI, qualification logic
7. 🔄 **Knockout Bracket** - Progressive building, final predictions
8. 🔄 **Scoring Engine** - Auto-calculate points after results
9. 🔄 **Leaderboard** - Rankings, pagination, global view
10. 🔄 **Competition Teams** - Create, join, aggregate scores, compare

---

## 📈 STATISTICS

- **🌍 48 National Teams** participating
- **⚽ 104 Matches** across 7 rounds (group + knockout)
- **🏟️ 12 Groups** with 4 teams each (group stage)
- **🏆 12 Third-Place Teams** (8 advance to knockout)
- **🎮 Unlimited Users** can register and compete
- **👥 Dynamic Competition Teams** for group play

---

## 🔒 SECURITY FEATURES

- ✅ **bcrypt Password Hashing** - Industry-standard protection
- ✅ **30-Day Session Cookies** - Auto-expiry for security
- ✅ **Admin Authentication** - Protected routes for data entry
- ✅ **UNIQUE Constraints** - Prevent duplicate predictions & memberships
- ✅ **Cookie Consent Tracking** - GDPR-friendly

---

## 🎨 UI/UX HIGHLIGHTS

- 🌐 **Responsive Design** - Works on desktop, tablet, mobile
- 🎯 **Real-Time Standings** - Live group standings calculation
- 🖱️ **Drag-and-Drop** - Intuitive third-place ranking interface
- 📊 **Visual Bracket** - Beautiful knockout bracket display
- 🎨 **TailwindCSS Styling** - Modern, clean, professional UI
- ⚡ **Fast Load Times** - Compiled CSS, optimized static files

---

## 💡 WHY THIS STACK?

| Choice | Reason |
|--------|--------|
| **FastAPI** | Modern, fast, automatic API docs, async support |
| **SQLModel** | Combines SQLAlchemy + Pydantic, best of both worlds |
| **SQLite** | Zero setup, file-based, perfect for self-contained app |
| **TailwindCSS** | Rapid UI development, utility-first, responsive |
| **Jinja2** | Powerful templating, works seamlessly with FastAPI |
| **bcrypt** | Battle-tested password security standard |

---

## 📝 NOTES

- Database: **SQLite** (worldcup.db) - auto-created on first run
- Python version: **3.13+** (required)
- Node version: **14+** (for TailwindCSS tooling)
- Admin access: Configure via environment variables or hardcoded (see Phase 3)

---

## 🎉 YOU'RE READY TO PREDICT!

The stage is set. The tournament awaits. **Make your predictions, earn your points, and become a FIFA World Cup 2026 prediction CHAMPION!** ⚽🏆

---

*Built with ❤️ for FIFA World Cup 2026 enthusiasts everywhere*
