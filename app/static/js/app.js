// ============================================
// URL State Management for Bracket Predictions
// ============================================

// Global state object
window.bracketState = {
    version: 1,
    groupPredictions: {},      // matchNumber -> { outcome, homeScore, awayScore }
    knockoutPredictions: {},   // matchNumber -> { outcome, homeScore, awayScore, penaltyWinner }
    thirdPlaceRanking: []      // Array of team IDs in rank order
};

// Match data populated by templates (keyed by match number)
// Use existing data if already set by template, otherwise initialize empty
window.matchData = window.matchData || {};

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Load state from URL on page load
    loadStateFromURL();
});

// ============================================
// URL Encoding/Decoding (using pako for compression)
// ============================================

function encodeState(state) {
    try {
        const json = JSON.stringify(state);
        const compressed = pako.deflate(json, { level: 9 });
        return base64UrlEncode(compressed);
    } catch (e) {
        console.error('Failed to encode state:', e);
        return null;
    }
}

function decodeState(encodedStr) {
    try {
        const compressed = base64UrlDecode(encodedStr);
        const json = pako.inflate(compressed, { to: 'string' });
        return JSON.parse(json);
    } catch (e) {
        console.error('Failed to decode state:', e);
        return null;
    }
}

function base64UrlEncode(bytes) {
    return btoa(String.fromCharCode.apply(null, bytes))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

function base64UrlDecode(str) {
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4) str += '=';
    return new Uint8Array(atob(str).split('').map(c => c.charCodeAt(0)));
}

// ============================================
// State Loading and URL Management
// ============================================

function loadStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    const stateParam = params.get('s');

    if (stateParam) {
        const decodedState = decodeState(stateParam);
        if (decodedState) {
            window.bracketState = decodedState;
            applyStateToUI();
        }
    }
}

function updateURLState() {
    const encoded = encodeState(window.bracketState);
    if (encoded) {
        const newURL = `${window.location.pathname}?s=${encoded}`;
        window.history.replaceState({}, '', newURL);
    }
}

function copyShareableLink() {
    const encoded = encodeState(window.bracketState);
    if (!encoded) {
        showToast('Failed to generate link', 'error');
        return;
    }

    const shareURL = `${window.location.origin}${window.location.pathname}?s=${encoded}`;

    navigator.clipboard.writeText(shareURL).then(() => {
        showToast('Link copied to clipboard!', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const input = document.createElement('input');
        input.value = shareURL;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        showToast('Link copied to clipboard!', 'success');
    });
}

// ============================================
// Apply State to UI
// ============================================

function applyStateToUI() {
    const state = window.bracketState;

    // Apply group predictions
    Object.entries(state.groupPredictions || {}).forEach(([matchNum, pred]) => {
        applyPredictionToUI(matchNum, pred);
    });

    // Apply knockout predictions
    Object.entries(state.knockoutPredictions || {}).forEach(([matchNum, pred]) => {
        applyPredictionToUI(matchNum, pred);
    });

    // Apply third place ranking if the function exists
    if (state.thirdPlaceRanking && state.thirdPlaceRanking.length > 0 && typeof applyThirdPlaceRanking === 'function') {
        applyThirdPlaceRanking(state.thirdPlaceRanking);
    }

    // Recalculate standings if the function exists
    if (typeof recalculateAllStandings === 'function') {
        recalculateAllStandings();
    }
}

function applyPredictionToUI(matchNum, pred) {
    const matchCard = document.querySelector(`[data-match-number="${matchNum}"]`);
    if (!matchCard) return;

    // Clear existing selections
    matchCard.querySelectorAll('.prediction-btn').forEach(btn => {
        btn.classList.remove('selected');
    });

    // Select the correct button
    if (pred.outcome) {
        const btn = matchCard.querySelector(`[data-outcome="${pred.outcome}"]`);
        if (btn) btn.classList.add('selected');
    }

    // Set score inputs
    const homeScoreInput = matchCard.querySelector('.home-score');
    const awayScoreInput = matchCard.querySelector('.away-score');
    if (homeScoreInput && pred.homeScore !== undefined && pred.homeScore !== null) {
        homeScoreInput.value = pred.homeScore;
    }
    if (awayScoreInput && pred.awayScore !== undefined && pred.awayScore !== null) {
        awayScoreInput.value = pred.awayScore;
    }

    // Handle penalty winner for knockout draws
    if (pred.outcome === 'draw' && pred.penaltyWinner) {
        const penaltySelect = matchCard.querySelector('.penalty-winner-select');
        if (penaltySelect) {
            penaltySelect.value = pred.penaltyWinner;
            // Show penalty picker if hidden
            const penaltyPicker = matchCard.querySelector('.penalty-picker');
            if (penaltyPicker) {
                penaltyPicker.classList.remove('hidden');
            }
        }
    }
}

// ============================================
// Save Predictions (Client-Side)
// ============================================

function savePredictionLocal(matchNumber, outcome, homeScore = null, awayScore = null, penaltyWinner = null, isBulkOperation = false) {
    const isKnockout = matchNumber > 72;

    if (isKnockout) {
        window.bracketState.knockoutPredictions[matchNumber] = {
            outcome,
            homeScore,
            awayScore,
            penaltyWinner
        };
    } else {
        window.bracketState.groupPredictions[matchNumber] = {
            outcome,
            homeScore,
            awayScore
        };
    }

    updateURLState();

    // Recalculate standings if the function exists
    if (typeof recalculateAllStandings === 'function') {
        recalculateAllStandings();
    }

    // Show success toast (unless bulk operation)
    if (!isBulkOperation) {
        showToast('Prediction saved!', 'success');
    }
}

function saveThirdPlaceRanking(rankings) {
    window.bracketState.thirdPlaceRanking = rankings;
    updateURLState();
    showToast('Rankings saved!', 'success');
}

function deletePredictionLocal(matchNumber) {
    const isKnockout = matchNumber > 72;

    if (isKnockout) {
        delete window.bracketState.knockoutPredictions[matchNumber];
    } else {
        delete window.bracketState.groupPredictions[matchNumber];
    }

    updateURLState();

    // Clear UI
    const matchCard = document.querySelector(`[data-match-number="${matchNumber}"]`);
    if (matchCard) {
        matchCard.querySelectorAll('.prediction-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        const homeScoreInput = matchCard.querySelector('.home-score');
        const awayScoreInput = matchCard.querySelector('.away-score');
        if (homeScoreInput) homeScoreInput.value = '';
        if (awayScoreInput) awayScoreInput.value = '';
    }

    if (typeof recalculateAllStandings === 'function') {
        recalculateAllStandings();
    }
}

function resetAllPredictions() {
    if (!confirm('Are you sure you want to reset all predictions?')) {
        return;
    }

    window.bracketState = {
        version: 1,
        groupPredictions: {},
        knockoutPredictions: {},
        thirdPlaceRanking: []
    };

    updateURLState();

    // Clear all UI selections
    document.querySelectorAll('.prediction-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    document.querySelectorAll('.home-score, .away-score').forEach(input => {
        input.value = '';
    });

    if (typeof recalculateAllStandings === 'function') {
        recalculateAllStandings();
    }

    showToast('All predictions cleared', 'success');
}

// ============================================
// UI Helpers
// ============================================

function selectPrediction(matchNumber, outcome) {
    const matchCard = document.querySelector(`[data-match-number="${matchNumber}"]`);
    if (!matchCard) return;

    const buttons = matchCard.querySelectorAll('.prediction-btn');
    buttons.forEach(btn => {
        btn.classList.remove('selected');
        if (btn.dataset.outcome === outcome) {
            btn.classList.add('selected');
        }
    });
}

function updateScoreOutcome(matchNumber) {
    const matchCard = document.querySelector(`[data-match-number="${matchNumber}"]`);
    if (!matchCard) return;

    const homeScore = parseInt(matchCard.querySelector('.home-score')?.value) || 0;
    const awayScore = parseInt(matchCard.querySelector('.away-score')?.value) || 0;

    let outcome;
    if (homeScore > awayScore) {
        outcome = 'home_win';
    } else if (awayScore > homeScore) {
        outcome = 'away_win';
    } else {
        outcome = 'draw';
    }

    selectPrediction(matchNumber, outcome);
    return { outcome, homeScore, awayScore };
}

// ============================================
// Toast Notifications
// ============================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 p-4 rounded-lg shadow-md z-50 transition-opacity duration-300 border ${
        type === 'success' ? 'bg-green-50 text-green-800 border-green-200' :
        type === 'error' ? 'bg-red-50 text-red-800 border-red-200' :
        'bg-blue-50 text-blue-800 border-blue-200'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================
// Client-Side Standings Calculation
// ============================================

function calculateGroupStandings(groupLetter, teams, predictions) {
    const teamStats = {};

    // Initialize team stats
    teams.forEach(team => {
        teamStats[team.id] = {
            team_id: team.id,
            team_name: team.name,
            country_code: team.country_code,
            played: 0,
            won: 0,
            drawn: 0,
            lost: 0,
            goals_for: 0,
            goals_against: 0,
            points: 0
        };
    });

    // Process predictions for this group
    Object.entries(predictions).forEach(([matchNum, pred]) => {
        // Convert to string for consistent lookup (match data keys are strings from JSON)
        const matchInfo = window.matchData[String(matchNum)] || window.matchData[parseInt(matchNum)];
        if (!matchInfo || matchInfo.group !== groupLetter) return;

        const homeStats = teamStats[matchInfo.homeTeamId];
        const awayStats = teamStats[matchInfo.awayTeamId];

        if (!homeStats || !awayStats) return;

        homeStats.played++;
        awayStats.played++;

        const homeScore = pred.homeScore || 0;
        const awayScore = pred.awayScore || 0;

        homeStats.goals_for += homeScore;
        homeStats.goals_against += awayScore;
        awayStats.goals_for += awayScore;
        awayStats.goals_against += homeScore;

        if (pred.outcome === 'home_win') {
            homeStats.won++;
            homeStats.points += 3;
            awayStats.lost++;
        } else if (pred.outcome === 'away_win') {
            awayStats.won++;
            awayStats.points += 3;
            homeStats.lost++;
        } else {
            homeStats.drawn++;
            awayStats.drawn++;
            homeStats.points++;
            awayStats.points++;
        }
    });

    // Calculate goal difference and sort
    return Object.values(teamStats)
        .map(s => ({ ...s, goal_diff: s.goals_for - s.goals_against }))
        .sort((a, b) => {
            if (b.points !== a.points) return b.points - a.points;
            if (b.goal_diff !== a.goal_diff) return b.goal_diff - a.goal_diff;
            return b.goals_for - a.goals_for;
        });
}

// Form validation (legacy support)
function validatePredictionForm(form) {
    const predictions = form.querySelectorAll('input[name^="prediction_"]');
    let valid = true;

    predictions.forEach(input => {
        if (!input.value) {
            valid = false;
            const matchCard = input.closest('.match-card');
            if (matchCard) {
                matchCard.classList.add('border-red-500', 'border-2');
            }
        }
    });

    if (!valid) {
        alert('Please make a prediction for all matches.');
    }

    return valid;
}
