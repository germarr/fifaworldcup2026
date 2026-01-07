# FIFA World Cup Bracket Predictor

A web application for predicting FIFA World Cup match outcomes and creating your perfect tournament bracket. Similar to March Madness brackets, but for soccer!

## Features

- **User Authentication**: Register with username, password, and favorite team
- **Cookie Consent**: GDPR-compliant cookie consent banner
- **Dual Prediction Modes**:
  - **All At Once**: View and predict all matches in a scrollable grid
  - **Individual**: Select and predict matches one at a time
- **Real-time Validation**: Instant feedback on predictions
- **View Predictions**: Review all your bracket predictions in one place
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite with SQLModel ORM
- **Templates**: Jinja2
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Authentication**: Session-based with secure cookies

## Project Structure

```
fifa_worldcup/
├── app/
│   ├── models.py          # Database models
│   ├── database.py        # Database connection
│   ├── auth.py            # Authentication utilities
│   ├── dependencies.py    # FastAPI dependencies
│   └── routers/
│       ├── auth.py        # Auth routes (login, register, logout)
│       ├── brackets.py    # Bracket viewing routes
│       └── api.py         # API endpoints for predictions
├── simulations/
│   ├── seed_data.py       # Database seeder
│   ├── seed_player.py     # Player seeder with predictions
│   └── simulate_full_tournament.py # Tournament simulator
├── mockups/
│   ├── export_group_matches_csv.py # Export matches to CSV
│   ├── import_group_results_csv.py # Import results from CSV
│   └── generate_user_picks.py      # Generate test predictions
├── static/
│   ├── css/
│   │   └── styles.css     # Application styles
│   └── js/
│       ├── cookies.js     # Cookie consent handling
│       └── bracket.js     # Bracket interactions
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Home page
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── bracket_select.html # Bracket selection
│   └── bracket_view.html  # View predictions
├── main.py                # Application entry point
└── pyproject.toml         # Project dependencies
```

## Installation

1. **Clone the repository** (if applicable)

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Seed the database**:
   ```bash
   uv run python simulations/seed_data.py
   ```

   This will create:
   - 32 World Cup teams across 8 groups
   - 63 matches (48 group stage + 15 knockout)

## Running the Application

Start the development server:

```bash
uv run python main.py
```

Or use uvicorn directly:

```bash
uv run uvicorn main:app --reload
```

The application will be available at: `http://localhost:8000`

## Usage

### 1. Register an Account

1. Visit the home page
2. Click "Get Started" or "Register"
3. Enter:
   - Username (at least 3 characters)
   - Password (6-72 characters)
   - Favorite Team
4. Accept cookie consent

### 2. Make Predictions

**All At Once Mode**:
- View all matches in a grid
- Enter scores for each match
- Click "Save All Predictions" when done

**Individual Mode**:
- Click on any match from the list
- Enter scores in the modal
- Save each prediction individually

### 3. View Your Bracket

- Click "View Predictions" in the navigation
- See all your predictions with:
  - Match details
  - Your predicted scores
  - Predicted winners
  - Summary statistics

## Database Models

### User
- Username (unique)
- Password (hashed with bcrypt)
- Favorite team
- Cookie consent status
- Registration date

### Team
- Name (e.g., "Brazil")
- Code (e.g., "BRA")
- Group (A-H)

### Match
- Round (Group Stage, Round of 16, etc.)
- Match number
- Teams (team1 vs team2)
- Match date
- Actual scores (for finished matches)

### Prediction
- User ID
- Match ID
- Predicted scores for both teams
- Predicted winner
- Timestamps

### Session
- User ID
- Session token (secure, random)
- Expiry (7 days)

## API Endpoints

### Authentication
- `GET /` - Home page
- `GET /register` - Registration form
- `POST /register` - Create account
- `GET /login` - Login form
- `POST /login` - Authenticate
- `POST /logout` - End session

### Brackets
- `GET /bracket` - Bracket selection page
- `GET /bracket/view` - View all predictions

### API
- `GET /api/matches` - Get all matches
- `GET /api/predictions` - Get user predictions
- `POST /api/predictions` - Create/update single prediction
- `POST /api/predictions/bulk` - Create/update multiple predictions

### Health
- `GET /health` - Health check

## Security Features

- Password hashing with bcrypt
- Session-based authentication with secure HTTP-only cookies
- CSRF protection via session tokens
- Cookie consent management
- SQL injection prevention (SQLModel ORM)
- Input validation on all forms

## Customization

### Add More Teams
Edit `simulations/seed_data.py` and add teams to the `teams_data` list.

### Change Match Schedule
Modify the match creation logic in `simulations/seed_data.py`.

### Styling
Edit `static/css/styles.css` to customize colors, fonts, and layout.

## Future Enhancements

- Points system for correct predictions
- Leaderboard to compare with other users
- Social sharing of brackets
- Lock predictions after matches start
- Live score updates
- Email notifications
- OAuth login (Google, Facebook)
- Mobile app

## Development

### Run Tests
```bash
# (Tests to be implemented)
pytest
```

### Seed Sample Data
```bash
# Seed teams and matches
uv run python simulations/seed_data.py

# Simulate tournament results
uv run python simulations/simulate_full_tournament.py

# Generate predictions for existing user
uv run python mockups/generate_user_picks.py <username>

# Create new player with automatic predictions
uv run python simulations/seed_player.py <username> <password> <favorite_team> [team_name]
```

### Seed New Players
The `simulations/seed_player.py` script quickly creates new players with automatic tournament predictions:

```bash
# Create new player (randomly assigned to a team)
python simulations/seed_player.py john password123 Brazil

# Create new player and assign to specific team
python simulations/seed_player.py alice mypass123 Argentina Phoenix

# Available teams: Phoenix, Dragons, Tigers, Eagles
```

Each new player:
- Gets assigned to one of 4 player teams
- Receives automatic predictions for all 64 matches
- Has predictions that follow tournament logic (group stage → knockout)

### Database Reset
```bash
rm worldcup.db && uv run python simulations/seed_data.py
```

### Enable Debug Mode
Set `echo=True` in `app/database.py` to see SQL queries.

## License

This project is for educational and personal use.

## Author

Built with FastAPI, SQLModel, and Jinja2.
