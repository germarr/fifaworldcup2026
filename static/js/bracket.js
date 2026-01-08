// FIFA World Cup Bracket Prediction - Game Mode & Individual Mode

const FLAG_MAPPING = {
    "ARG": "ar", "AUS": "au", "BEL": "be", "BRA": "br", "CAN": "ca",
    "CMR": "cm", "CRC": "cr", "CRO": "hr", "DEN": "dk", "ECU": "ec",
    "ENG": "gb-eng", "ESP": "es", "FRA": "fr", "GER": "de", "GHA": "gh",
    "IRN": "ir", "JPN": "jp", "KOR": "kr", "KSA": "sa", "MAR": "ma",
    "MEX": "mx", "NED": "nl", "POL": "pl", "POR": "pt", "QAT": "qa",
    "SEN": "sn", "SRB": "rs", "SUI": "ch", "TUN": "tn", "URU": "uy",
    "USA": "us", "WAL": "gb-wls"
};

class BracketGame {
    constructor() {
        this.currentIndex = 0;
        this.matches = [];
        this.predictions = {};
        this.standings = {};
        this.flagMapping = FLAG_MAPPING;
    }

    async init() {
        await this.loadMatches();
        await this.loadPredictions();
        await this.loadStandings();
        this.showMatch(this.currentIndex);
        this.setupEventListeners();
    }

    async loadMatches() {
        try {
            const response = await fetch('/api/matches');
            this.matches = await response.json();
            document.getElementById('total-matches').textContent = this.matches.length;
        } catch (error) {
            console.error('Error loading matches:', error);
            showNotification('Failed to load matches', 'error');
        }
    }

    async loadPredictions() {
        try {
            const response = await fetch('/api/predictions');
            const predictionsArray = await response.json();

            // Convert array to map for easier lookup
            this.predictions = {};
            predictionsArray.forEach(pred => {
                this.predictions[pred.match_id] = pred;
            });
        } catch (error) {
            console.error('Error loading predictions:', error);
        }
    }

    async loadStandings() {
        try {
            const response = await fetch('/api/standings');
            this.standings = await response.json();
            this.updateStandingsDashboard();
        } catch (error) {
            console.error('Error loading standings:', error);
        }
    }

    showMatch(index) {
        if (index < 0 || index >= this.matches.length) {
            return;
        }

        this.currentIndex = index;
        const match = this.matches[index];

        // Update match info
        document.getElementById('card-round').textContent = match.round;
        document.getElementById('card-match-number').textContent = `Match #${match.match_number}`;
        document.getElementById('current-match-num').textContent = index + 1;
        document.getElementById('current-round').textContent = match.round;

        // Update date
        const matchDate = new Date(match.match_date);
        document.getElementById('card-date').textContent = matchDate.toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric'
        });

        // Update teams
        document.getElementById('team1-name').textContent = match.team1_name;
        document.getElementById('team2-name').textContent = match.team2_name;

        // Update team flags (use country code or placeholder)
        const team1FlagContainer = document.getElementById('team1-flag');
        const team2FlagContainer = document.getElementById('team2-flag');

        const updateFlag = (container, code, placeholder) => {
            if (code && FLAG_MAPPING[code]) {
                const countryCode = FLAG_MAPPING[code];
                container.innerHTML = `<img src="https://flagcdn.com/w160/${countryCode}.png" alt="${code}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
                container.className = 'team-flag has-img';
            } else {
                container.textContent = placeholder || 'TBD';
                container.className = 'team-flag placeholder';
            }
        };

        updateFlag(team1FlagContainer, match.team1_code, match.team1_placeholder);
        updateFlag(team2FlagContainer, match.team2_code, match.team2_placeholder);

        // Update penalty shootout options with team names and IDs
        document.getElementById('penalty-option-team1').textContent = match.team1_name;
        document.getElementById('penalty-option-team1').value = match.team1_id || '';
        document.getElementById('penalty-option-team2').textContent = match.team2_name;
        document.getElementById('penalty-option-team2').value = match.team2_id || '';

        // Load existing prediction if available
        const prediction = this.predictions[match.id];
        if (prediction) {
            document.getElementById('team1-score').value = prediction.predicted_team1_score;
            document.getElementById('team2-score').value = prediction.predicted_team2_score;

            // Check if penalty shootout should be shown
            this.updatePenaltyShootoutVisibility(match, prediction.predicted_team1_score, prediction.predicted_team2_score);

            // Set penalty winner if exists
            if (prediction.penalty_shootout_winner_id) {
                document.getElementById('penalty-winner').value = prediction.penalty_shootout_winner_id;
            } else {
                document.getElementById('penalty-winner').value = '';
            }
        } else {
            // Default to 0-0 instead of empty
            document.getElementById('team1-score').value = 0;
            document.getElementById('team2-score').value = 0;
            document.getElementById('penalty-shootout-container').style.display = 'none';
            document.getElementById('penalty-winner').value = '';
        }

        // Update progress bar
        const progress = ((index + 1) / this.matches.length) * 100;
        document.getElementById('progress-fill').style.width = `${progress}%`;

        // Update button states
        document.getElementById('prev-btn').disabled = (index === 0);
        document.getElementById('next-btn').disabled = false;

        // Hide completion message
        document.getElementById('completion-message').style.display = 'none';
        document.getElementById('match-card-container').querySelector('.match-header').style.display = 'flex';
        document.getElementById('match-card-container').querySelector('.match-teams-large').style.display = 'flex';
        document.getElementById('match-card-container').querySelector('.game-navigation').style.display = 'flex';

        // Check if this is the last match
        if (index === this.matches.length - 1) {
            document.getElementById('next-btn').textContent = 'Finish';
        } else {
            document.getElementById('next-btn').innerHTML = '<span>Next →</span>';
        }
    }

    updatePenaltyShootoutVisibility(match, team1Score, team2Score) {
        const penaltyContainer = document.getElementById('penalty-shootout-container');
        const isKnockout = !match.round.includes('Group Stage');
        const isTied = team1Score !== '' && team2Score !== '' && parseInt(team1Score) === parseInt(team2Score);

        if (isKnockout && isTied) {
            penaltyContainer.style.display = 'block';
        } else {
            penaltyContainer.style.display = 'none';
        }
    }

    async saveCurrentPrediction() {
        const match = this.matches[this.currentIndex];
        const team1Score = document.getElementById('team1-score').value;
        const team2Score = document.getElementById('team2-score').value;

        // Allow empty/0 scores for navigation but need validation
        // For group stage, allow empty (optional)
        // For knockout, if different scores (no tie) allow empty, if tied need penalty
        const isKnockout = !match.round.includes('Group Stage');
        
        // If scores are truly empty (not just 0), allow navigation without saving
        if (team1Score === '' && team2Score === '') {
            return true;
        }

        // Ensure both scores have values (default to 0 if one is empty but not both)
        const score1 = team1Score === '' ? 0 : parseInt(team1Score);
        const score2 = team2Score === '' ? 0 : parseInt(team2Score);

        // Check if penalty shootout winner is needed
        const isTied = score1 === score2;
        const penaltyWinner = document.getElementById('penalty-winner').value;

        if (isKnockout && isTied && !penaltyWinner) {
            showNotification('Please select a penalty shootout winner for tied knockout matches', 'error');
            return false;
        }

        try {
            const payload = {
                match_id: match.id,
                predicted_team1_score: score1,
                predicted_team2_score: score2
            };

            // Add penalty shootout winner if applicable
            if (isKnockout && isTied && penaltyWinner) {
                payload.penalty_shootout_winner_id = parseInt(penaltyWinner);
            }

            const response = await fetch('/api/predictions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const savedPrediction = await response.json();
                this.predictions[match.id] = savedPrediction;

                // Reload standings if this was a group stage match
                if (match.round.includes('Group Stage')) {
                    await this.loadStandings();
                }

                // Reload matches to update knockout teams
                await this.loadMatches();

                return true;
            } else {
                const error = await response.json();
                showNotification(error.detail || 'Failed to save prediction', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error saving prediction:', error);
            showNotification('Network error. Please try again.', 'error');
            return false;
        }
    }

    async goToNext() {
        // Save current prediction
        const saved = await this.saveCurrentPrediction();

        if (!saved) {
            return; // Don't navigate if save failed
        }

        if (this.currentIndex < this.matches.length - 1) {
            this.showMatch(this.currentIndex + 1);
        } else {
            // Reached the end
            this.showCompletionMessage();
        }
    }

    goToPrevious() {
        if (this.currentIndex > 0) {
            this.showMatch(this.currentIndex - 1);
        }
    }

    async skip() {
        // Just navigate without saving
        if (this.currentIndex < this.matches.length - 1) {
            this.showMatch(this.currentIndex + 1);
        } else {
            this.showCompletionMessage();
        }
    }

    showCompletionMessage() {
        document.getElementById('match-card-container').querySelector('.match-header').style.display = 'none';
        document.getElementById('match-card-container').querySelector('.match-date').style.display = 'none';
        document.getElementById('match-card-container').querySelector('.match-teams-large').style.display = 'none';
        document.getElementById('match-card-container').querySelector('.game-navigation').style.display = 'none';
        document.getElementById('completion-message').style.display = 'block';
    }

    updateStandingsDashboard() {
        const dashboard = document.getElementById('standings-dashboard');

        if (!this.standings || Object.keys(this.standings).length === 0) {
            dashboard.innerHTML = '<h3 class="section-title">Group Standings Dashboard</h3><p class="no-standings">Make predictions for group stage matches to see standings</p>';
            return;
        }

        let html = '<h3 class="section-title">Group Standings Dashboard</h3><div class="standings-grid">';

        // Helper to build flag URL
        const buildFlagUrl = (teamCode) => {
            if (!teamCode || !FLAG_MAPPING[teamCode]) {
                return '';
            }
            const code = FLAG_MAPPING[teamCode];
            return `https://flagcdn.com/w40/${code}.png`;
        };

        // Sort groups alphabetically
        const groups = Object.keys(this.standings).sort();

        groups.forEach(groupLetter => {
            const standings = this.standings[groupLetter];

            html += `
                <div class="group-standings">
                    <h4>Group ${groupLetter}</h4>
                    <table class="standings-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Team</th>
                                <th>Pts</th>
                                <th>W</th>
                                <th>L</th>
                                <th>D</th>
                                <th>GF</th>
                                <th>GA</th>
                                <th>GD</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            standings.forEach((team, index) => {
                const qualified = index < 2 ? 'qualified' : '';
                const gdClass = team.goal_difference >= 0 ? 'positive' : 'negative';
                
                const flagUrl = team.team_flag_url || buildFlagUrl(team.team_code);
                const flagHtml = flagUrl
                    ? `<img class="standings-flag" src="${flagUrl}" alt="${team.team_name} flag">`
                    : '';

                html += `
                    <tr class="${qualified}">
                        <td>${index + 1}</td>
                        <td class="team-name-cell">
                            <span class="team-name-row">
                                ${flagHtml}
                                <span class="team-code">${team.team_code}</span>
                            </span>
                            <span class="team-name-short">${team.team_name}</span>
                        </td>
                        <td class="points">${team.points}</td>
                        <td class="record-stat wins">${team.won}</td>
                        <td class="record-stat losses">${team.lost}</td>
                        <td class="record-stat draws">${team.drawn}</td>
                        <td class="goals-cell">${team.goals_for}</td>
                        <td class="goals-cell">${team.goals_against}</td>
                        <td class="goals-cell ${gdClass}">${team.goal_difference >= 0 ? '+' : ''}${team.goal_difference}</td>
                    </tr>
                `;
            });

            html += `
                        </tbody>
                    </table>
                </div>
            `;
        });

        html += '</div>';
        dashboard.innerHTML = html;
    }

    async pickForMe() {
        showNotification('Generating a random pick for this match...', 'success');

        try {
            const match = this.matches[this.currentIndex];
            const team1Score = Math.floor(Math.random() * 5);
            const team2Score = Math.floor(Math.random() * 5);

            const payload = {
                match_id: match.id,
                predicted_team1_score: team1Score,
                predicted_team2_score: team2Score
            };

            const isKnockout = !match.round.includes('Group Stage');
            if (isKnockout && team1Score === team2Score) {
                payload.penalty_shootout_winner_id = Math.random() > 0.5 ? match.team1_id : match.team2_id;
            }

            const response = await fetch('/api/predictions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const savedPrediction = await response.json();
                this.predictions[match.id] = savedPrediction;
            } else {
                const error = await response.json();
                showNotification(error.detail || 'Failed to save prediction', 'error');
                return;
            }

            await this.loadStandings();
            await this.loadMatches();
            this.showMatch(this.currentIndex);
            showNotification('🎲 Picked this match! You can edit the scores before moving on.', 'success');
        } catch (error) {
            console.error('Error in pickForMe:', error);
            showNotification('Network error. Please try again.', 'error');
        }
    }

    async simulateTournament() {
        showNotification('Simulating full tournament...', 'success');

        try {
            const response = await fetch('/api/simulate-tournament', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const error = await response.json();
                showNotification(error.detail || 'Simulation failed', 'error');
                return;
            }

            await this.loadStandings();
            await this.loadMatches();
            this.showMatch(this.currentIndex);
            showNotification('🏆 Tournament simulated! Actual results are now available.', 'success');
        } catch (error) {
            console.error('Error simulating tournament:', error);
            showNotification('Network error. Please try again.', 'error');
        }
    }

    setupEventListeners() {
        // Next button
        document.getElementById('next-btn').addEventListener('click', () => {
            this.goToNext();
        });

        // Previous button
        document.getElementById('prev-btn').addEventListener('click', () => {
            this.goToPrevious();
        });

        // Skip button
        document.getElementById('skip-btn').addEventListener('click', () => {
            this.skip();
        });

        // Pick for me button
        const pickForMeBtn = document.getElementById('pick-for-me-btn');
        if (pickForMeBtn) {
            pickForMeBtn.addEventListener('click', () => {
                this.pickForMe();
            });
        }

        const pickEntireTournamentBtn = document.getElementById('pick-entire-tournament-btn');
        if (pickEntireTournamentBtn) {
            pickEntireTournamentBtn.addEventListener('click', () => {
                if (confirm('This will simulate the entire tournament and overwrite official results. Continue?')) {
                    this.simulateTournament();
                }
            });
        }

        // Score change listeners to update penalty shootout visibility
        const team1ScoreInput = document.getElementById('team1-score');
        const team2ScoreInput = document.getElementById('team2-score');

        const updatePenalty = () => {
            const match = this.matches[this.currentIndex];
            const team1Score = team1ScoreInput.value;
            const team2Score = team2ScoreInput.value;
            this.updatePenaltyShootoutVisibility(match, team1Score, team2Score);
        };

        team1ScoreInput.addEventListener('input', updatePenalty);
        team2ScoreInput.addEventListener('input', updatePenalty);

        // Allow Enter key to go to next
        team1ScoreInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('team2-score').focus();
            }
        });

        team2ScoreInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.goToNext();
            }
        });
    }
}

// Initialize game mode
let bracketGame = null;

document.addEventListener('DOMContentLoaded', function() {
    // Mode switching
    const modeAllBtn = document.getElementById('mode-all');
    const modeIndividualBtn = document.getElementById('mode-individual');
    const allAtOnceMode = document.getElementById('all-at-once-mode');
    const individualMode = document.getElementById('individual-mode');
    const standingsDashboard = document.getElementById('standings-dashboard');

    // Initialize game mode
    if (modeAllBtn && allAtOnceMode.style.display !== 'none') {
        bracketGame = new BracketGame();
        bracketGame.init();
    }

    // Switch to "Game Mode"
    if (modeAllBtn) {
        modeAllBtn.addEventListener('click', function() {
            modeAllBtn.classList.add('active');
            modeAllBtn.classList.remove('btn-secondary');
            modeAllBtn.classList.add('btn-primary');

            modeIndividualBtn.classList.remove('active');
            modeIndividualBtn.classList.remove('btn-primary');
            modeIndividualBtn.classList.add('btn-secondary');

            allAtOnceMode.style.display = 'block';
            individualMode.style.display = 'none';
            standingsDashboard.style.display = 'block';

            // Initialize game if not already
            if (!bracketGame) {
                bracketGame = new BracketGame();
                bracketGame.init();
            }
        });
    }

    // Switch to "Individual" mode
    if (modeIndividualBtn) {
        modeIndividualBtn.addEventListener('click', function() {
            modeIndividualBtn.classList.add('active');
            modeIndividualBtn.classList.remove('btn-secondary');
            modeIndividualBtn.classList.add('btn-primary');

            modeAllBtn.classList.remove('active');
            modeAllBtn.classList.remove('btn-primary');
            modeAllBtn.classList.add('btn-secondary');

            individualMode.style.display = 'block';
            allAtOnceMode.style.display = 'none';
            standingsDashboard.style.display = 'block';
        });
    }

    // Individual mode - score change listeners for penalty shootout visibility
    const individualCards = document.querySelectorAll('.individual-match-card');

    individualCards.forEach(card => {
        const matchId = card.dataset.matchId;
        const team1Input = card.querySelector('.team1-score');
        const team2Input = card.querySelector('.team2-score');
        const penaltyContainer = card.querySelector('.penalty-shootout-individual');

        if (penaltyContainer) {
            const updatePenaltyIndividual = () => {
                const team1Score = team1Input.value;
                const team2Score = team2Input.value;
                const isTied = team1Score !== '' && team2Score !== '' && parseInt(team1Score) === parseInt(team2Score);

                if (isTied) {
                    penaltyContainer.style.display = 'flex';
                } else {
                    penaltyContainer.style.display = 'none';
                }
            };

            team1Input.addEventListener('input', updatePenaltyIndividual);
            team2Input.addEventListener('input', updatePenaltyIndividual);

            // Check initial state
            updatePenaltyIndividual();
        }
    });

    // Individual mode save buttons
    const saveIndividualBtns = document.querySelectorAll('.save-individual-btn');

    const refreshIndividualMatches = async () => {
        try {
            const response = await fetch('/api/matches');
            if (!response.ok) {
                return;
            }
            const matches = await response.json();
            const matchesMap = new Map(matches.map(match => [match.id, match]));

            document.querySelectorAll('.individual-match-card').forEach(card => {
                const matchId = parseInt(card.dataset.matchId, 10);
                const match = matchesMap.get(matchId);
                if (!match) {
                    return;
                }

                const team1Container = card.querySelector('.individual-team:nth-child(1) .team-flag-small');
                const team1Name = card.querySelector('.individual-team:nth-child(1) .team-name-individual');
                const team2Container = card.querySelector('.individual-team:nth-child(3) .team-flag-small');
                const team2Name = card.querySelector('.individual-team:nth-child(3) .team-name-individual');

                const renderFlag = (container, code, placeholder) => {
                    if (!container) {
                        return;
                    }
                    if (code && FLAG_MAPPING[code]) {
                        const countryCode = FLAG_MAPPING[code];
                        container.innerHTML = `<img src="https://flagcdn.com/w40/${countryCode}.png" alt="${code}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;">`;
                    } else if (placeholder) {
                        container.textContent = placeholder;
                    } else {
                        container.textContent = 'TBD';
                    }
                };

                renderFlag(team1Container, match.team1_code, match.team1_placeholder);
                renderFlag(team2Container, match.team2_code, match.team2_placeholder);

                if (team1Name) {
                    team1Name.textContent = match.team1_code || match.team1_placeholder || 'TBD';
                }
                if (team2Name) {
                    team2Name.textContent = match.team2_code || match.team2_placeholder || 'TBD';
                }

                const penaltySelect = card.querySelector('.penalty-select-individual');
                if (penaltySelect) {
                    const options = penaltySelect.querySelectorAll('option');
                    if (options.length >= 3) {
                        options[1].textContent = match.team1_name || 'Team 1';
                        options[2].textContent = match.team2_name || 'Team 2';
                    }
                }
            });
        } catch (error) {
            console.error('Error refreshing matches:', error);
        }
    };

    saveIndividualBtns.forEach(btn => {
        btn.addEventListener('click', async function() {
            const matchId = this.dataset.matchId;
            const card = document.querySelector(`.individual-match-card[data-match-id="${matchId}"]`);
            const originalLabel = this.textContent;
            this.disabled = true;
            this.textContent = 'Saving...';

            const team1Score = card.querySelector('.team1-score').value;
            const team2Score = card.querySelector('.team2-score').value;

            // Validate that scores are entered
            if (team1Score === '' || team2Score === '') {
                showNotification('Please enter both scores', 'error');
                this.disabled = false;
                this.textContent = originalLabel;
                return;
            }

            const payload = {
                match_id: parseInt(matchId),
                predicted_team1_score: parseInt(team1Score),
                predicted_team2_score: parseInt(team2Score)
            };

            // Check for penalty shootout in knockout matches
            const penaltySelect = card.querySelector('.penalty-select-individual');
            if (penaltySelect && penaltySelect.style.display !== 'none') {
                const isTied = parseInt(team1Score) === parseInt(team2Score);
                const penaltyValue = penaltySelect.value;

                if (isTied && !penaltyValue) {
                    showNotification('Please select penalty shootout winner', 'error');
                    this.disabled = false;
                    this.textContent = originalLabel;
                    return;
                }

                if (isTied && penaltyValue) {
                    // Get team IDs from the card
                    const matchHeader = card.querySelector('.individual-match-header');
                    const roundText = matchHeader.querySelector('.match-round').textContent;

                    // Fetch match details to get team IDs
                    try {
                        const matchResponse = await fetch('/api/matches');
                        const matches = await matchResponse.json();
                        const match = matches.find(m => m.id === parseInt(matchId));

                        if (match) {
                            const teamId = penaltyValue === 'team1' ? match.team1_id : match.team2_id;
                            payload.penalty_shootout_winner_id = teamId;
                        }
                    } catch (error) {
                        console.error('Error fetching match details:', error);
                    }
                }
            }

            try {
                const response = await fetch('/api/predictions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    showNotification('Prediction saved!', 'success');

                    // Mark card as having prediction
                    card.classList.add('has-prediction');

                    // Reload standings if available and refresh individual matches
                    if (typeof loadStandingsDashboard === 'function') {
                        await loadStandingsDashboard();
                    }
                    await refreshIndividualMatches();
                } else {
                    const error = await response.json();
                    showNotification(error.detail || 'Failed to save prediction', 'error');
                }
            } catch (error) {
                showNotification('Network error. Please try again.', 'error');
            } finally {
                this.disabled = false;
                this.textContent = originalLabel;
            }
        });
    });
});

// Show notification message
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = 'notification';

    if (type === 'error') {
        notification.classList.add('error');
    }

    notification.style.display = 'block';

    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}
