// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }
});

// Prediction button selection
function selectPrediction(matchId, outcome) {
    const buttons = document.querySelectorAll(`[data-match="${matchId}"] .prediction-btn`);
    buttons.forEach(btn => {
        btn.classList.remove('selected');
        if (btn.dataset.outcome === outcome) {
            btn.classList.add('selected');
        }
    });

    // Update hidden input
    const input = document.querySelector(`input[name="prediction_${matchId}"]`);
    if (input) {
        input.value = outcome;
    }
}

// Score input handling
function updateScoreOutcome(matchId) {
    const homeScore = parseInt(document.querySelector(`input[name="home_score_${matchId}"]`)?.value) || 0;
    const awayScore = parseInt(document.querySelector(`input[name="away_score_${matchId}"]`)?.value) || 0;

    let outcome;
    if (homeScore > awayScore) {
        outcome = 'home_win';
    } else if (awayScore > homeScore) {
        outcome = 'away_win';
    } else {
        outcome = 'draw';
    }

    selectPrediction(matchId, outcome);
}

// Form validation
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

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 transition-opacity duration-300 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        'bg-fifa-blue text-white'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// AJAX prediction submission
async function submitPrediction(matchId, outcome, homeScore = null, awayScore = null) {
    try {
        const response = await fetch(`/api/predictions/match/${matchId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                predicted_outcome: outcome,
                predicted_home_score: homeScore,
                predicted_away_score: awayScore,
            }),
        });

        if (response.ok) {
            showToast('Prediction saved!', 'success');
            return true;
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to save prediction', 'error');
            return false;
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
        return false;
    }
}
