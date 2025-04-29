// static/js/live-predictions.js
class LivePredictions {
    constructor() {
        this.init();
    }

    async init() {
        const loadingSpinner = document.querySelector('.loading-spinner');
        const errorMessage = document.querySelector('.error-message');
        const predictionsContainer = document.getElementById('live-predictions');

        try {
            loadingSpinner.style.display = 'block';
            const response = await fetch('/api/predict-today');
            console.log('API Response:', response); // Debug log

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Predictions data:', data); // Debug log

            if (data.status === 'success' && data.predictions.length > 0) {
                this.displayPredictions(data.predictions);
            } else {
                predictionsContainer.innerHTML = '<div class="alert alert-info">No matches available for prediction at the moment.</div>';
            }
        } catch (error) {
            console.error('Error fetching predictions:', error);
            predictionsContainer.innerHTML = `
                <div class="alert alert-danger">
                    Error loading predictions. Please try again later.
                </div>
            `;
        } finally {
            loadingSpinner.style.display = 'none';
        }
    }

    displayPredictions(predictions) {
        const container = document.getElementById('live-predictions');
        if (!container) return;

        container.innerHTML = predictions.map(pred => `
            <div class="prediction-card">
                <div class="match-info">
                    <span class="competition">${pred.match.competition}</span>
                    <span class="kickoff">${new Date(pred.match.kickoff).toLocaleTimeString()}</span>
                </div>
                
                <div class="teams">
                    <span class="home-team">${pred.match.homeTeam}</span>
                    <span class="vs">vs</span>
                    <span class="away-team">${pred.match.awayTeam}</span>
                </div>

                <div class="prediction">
                    <h4>Predicted Outcome: ${pred.predictions['Match Outcome']}</h4>
                    <div class="probabilities">
                        <div class="prob-bar">
                            <label>Home Win</label>
                            <div class="bar">
                                <div class="fill" style="width: ${pred.probabilities['Match Outcome']['Home Win']}"></div>
                            </div>
                            <span>${pred.probabilities['Match Outcome']['Home Win']}</span>
                        </div>
                        <div class="prob-bar">
                            <label>Draw</label>
                            <div class="bar">
                                <div class="fill" style="width: ${pred.probabilities['Match Outcome']['Draw']}"></div>
                            </div>
                            <span>${pred.probabilities['Match Outcome']['Draw']}</span>
                        </div>
                        <div class="prob-bar">
                            <label>Away Win</label>
                            <div class="bar">
                                <div class="fill" style="width: ${pred.probabilities['Match Outcome']['Away Win']}"></div>
                            </div>
                            <span>${pred.probabilities['Match Outcome']['Away Win']}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        // Update last updated time
        document.getElementById('lastUpdated').textContent =
            `Last updated: ${new Date().toLocaleTimeString()}`;
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    new LivePredictions();
});