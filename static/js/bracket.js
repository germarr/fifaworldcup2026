// FIFA World Cup Bracket Prediction - Game Mode & Individual Mode

class BracketGame {
    constructor() {
        this.currentIndex = 0;
        this.matches = [];
        this.predictions = {};
        this.standings = {};
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
        const team1Flag = document.getElementById('team1-flag');
        const team2Flag = document.getElementById('team2-flag');

        if (match.team1_code) {
            team1Flag.textContent = match.team1_code;
            team1Flag.className = 'team-flag';
        } else {
            team1Flag.textContent = match.team1_placeholder || 'TBD';
            team1Flag.className = 'team-flag placeholder';
        }

        if (match.team2_code) {
            team2Flag.textContent = match.team2_code;
            team2Flag.className = 'team-flag';
        } else {
            team2Flag.textContent = match.team2_placeholder || 'TBD';
            team2Flag.className = 'team-flag placeholder';
        }

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
            document.getElementById('team1-score').value = '';
            document.getElementById('team2-score').value = '';
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

        // Skip if no scores entered
        if (team1Score === '' || team2Score === '') {
            return true; // Return success to allow navigation
        }

        // Check if penalty shootout winner is needed
        const isKnockout = !match.round.includes('Group Stage');
        const isTied = parseInt(team1Score) === parseInt(team2Score);
        const penaltyWinner = document.getElementById('penalty-winner').value;

        if (isKnockout && isTied && !penaltyWinner) {
            showNotification('Please select a penalty shootout winner for tied knockout matches', 'error');
            return false;
        }

        try {
            const payload = {
                match_id: match.id,
                predicted_team1_score: parseInt(team1Score),
                predicted_team2_score: parseInt(team2Score)
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
            dashboard.innerHTML = '<p class="no-standings">Make predictions for group stage matches to see standings</p>';
            return;
        }

        let html = '<div class="standings-grid">';

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
                            </tr>
                        </thead>
                        <tbody>
            `;

            standings.forEach((team, index) => {
                const qualified = index < 2 ? 'qualified' : '';
                html += `
                    <tr class="${qualified}">
                        <td>${index + 1}</td>
                        <td class="team-name-cell">
                            <span class="team-code">${team.team_code}</span>
                            <span class="team-name-short">${team.team_name}</span>
                        </td>
                        <td class="points">${team.points}</td>
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

    saveIndividualBtns.forEach(btn => {
        btn.addEventListener('click', async function() {
            const matchId = this.dataset.matchId;
            const card = document.querySelector(`.individual-match-card[data-match-id="${matchId}"]`);

            const team1Score = card.querySelector('.team1-score').value;
            const team2Score = card.querySelector('.team2-score').value;

            // Validate that scores are entered
            if (team1Score === '' || team2Score === '') {
                showNotification('Please enter both scores', 'error');
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

                    // Reload standings if game mode is active
                    if (bracketGame) {
                        await bracketGame.loadStandings();
                        await bracketGame.loadMatches();
                    }
                } else {
                    const error = await response.json();
                    showNotification(error.detail || 'Failed to save prediction', 'error');
                }
            } catch (error) {
                showNotification('Network error. Please try again.', 'error');
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
