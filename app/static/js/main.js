// static/js/main.js

class PredictionManager {
    constructor() {
        this.predictions = JSON.parse(localStorage.getItem('predictions') || '[]');
        this.updatePredictionsList();

        // Add this part to connect the save button
        document.addEventListener('click', (e) => {
            if (e.target.matches('.save-prediction') || e.target.matches('[onclick*="Save Prediction"]')) {
                e.preventDefault();
                this.savePrediction();
            }
        });
    }

    savePrediction() {
        const homeTeam = document.querySelector('select[name="homeTeam"]').value;
        const awayTeam = document.querySelector('select[name="awayTeam"]').value;

        const prediction = {
            id: Date.now(),
            date: new Date().toLocaleDateString(),
            homeTeam,
            awayTeam,
            matchOutcome: this.getPredictionValue('.match-outcome'),
            probabilities: {
                homeWin: this.getPredictionValue('.home-win-prob'),
                draw: this.getPredictionValue('.draw-prob'),
                awayWin: this.getPredictionValue('.away-win-prob')
            },
            goals: {
                over15: this.getPredictionValue('.over-1-5'),
                over25: this.getPredictionValue('.over-2-5'),
                btts: this.getPredictionValue('.btts')
            }
        };

        this.predictions.push(prediction);
        localStorage.setItem('predictions', JSON.stringify(this.predictions));
        this.updatePredictionsList();
        this.showNotification('Prediction saved successfully!');
    }

    getPredictionValue(selector) {
        const element = document.querySelector(selector);
        return element ? element.textContent.trim() : '';
    }

    updatePredictionsList() {
        const container = document.querySelector('.today-predictions');
        if (!container) return;

        console.log('Updating predictions list:', this.predictions); // Debug log

        const predictionsList = this.predictions.map(pred => `
            <div class="prediction-item">
                <div class="prediction-header">
                    <span class="date">${pred.date}</span>
                    <button class="btn-delete" onclick="predictionManager.deletePrediction(${pred.id})">×</button>
                </div>
                <div class="match-teams">
                    ${pred.homeTeam || ''} vs ${pred.awayTeam || ''} 
                </div>
                <div class="prediction-details">
                    <div class="outcome">
                        <strong>Outcome:</strong> ${pred.matchOutcome || ''}
                    </div>
                    <div class="goals">
                        <div>Over 1.5: ${pred.goals?.over15 || ''}</div>
                        <div>Over 2.5: ${pred.goals?.over25 || ''}</div>
                        <div>BTTS: ${pred.goals?.btts || ''}</div>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = predictionsList || '<p>No predictions saved yet</p>';
    }

    deletePrediction(id) {
        this.predictions = this.predictions.filter(p => p.id !== id);
        localStorage.setItem('predictions', JSON.stringify(this.predictions));
        this.updatePredictionsList();
        this.showNotification('Prediction deleted');
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => notification.remove(), 3000);
    }
}

// Initialize the prediction manager
const predictionManager = new PredictionManager();

// Initialize team selection logic
document.addEventListener('DOMContentLoaded', () => {
    const homeSelect = document.querySelector('select[name="homeTeam"]');
    const awaySelect = document.querySelector('select[name="awayTeam"]');

    function updateSelections() {
        const homeTeam = homeSelect.value;
        const awayTeam = awaySelect.value;

        Array.from(homeSelect.options).forEach(option => {
            option.disabled = option.value === awayTeam;
        });
        Array.from(awaySelect.options).forEach(option => {
            option.disabled = option.value === homeTeam;
        });
    }

    homeSelect?.addEventListener('change', updateSelections);
    awaySelect?.addEventListener('change', updateSelections);
});