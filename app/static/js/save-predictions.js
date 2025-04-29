document.addEventListener('DOMContentLoaded', function() {
    const saveButton = document.getElementById('savePredictionButton');
    const savedPredictionsList = document.getElementById('savedPredictionsList');

    if (saveButton) {
        saveButton.addEventListener('click', async function() {
            const homeTeam = document.getElementById('homeTeamSelected').value;
            const awayTeam = document.getElementById('awayTeamSelected').value;
            const predictions = JSON.parse(document.getElementById('predictionsData').textContent);

            const payload = {
                homeTeam,
                awayTeam,
                predictions,
                timestamp: new Date().toISOString()
            };

            try {
                const response = await fetch('/api/save-prediction', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (result.status === 'success') {
                    alert('✅ Prediction saved successfully!');
                    saveLocally(payload);
                    displaySavedPredictions();
                } else {
                    alert('❌ Failed to save prediction.');
                }

            } catch (error) {
                console.error('Error saving prediction:', error);
                alert('❌ Error saving prediction.');
            }
        });
    }

    function saveLocally(prediction) {
        let saved = JSON.parse(localStorage.getItem('savedPredictions')) || [];
        saved.push(prediction);
        localStorage.setItem('savedPredictions', JSON.stringify(saved));
    }

    function displaySavedPredictions() {
    if (!savedPredictionsList) return;

    const saved = JSON.parse(localStorage.getItem('savedPredictions')) || [];
    savedPredictionsList.innerHTML = '';

    saved.slice(-5).reverse().forEach((prediction, index) => {
        const div = document.createElement('div');
        div.className = 'saved-prediction-card';
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${prediction.homeTeam}</strong> vs <strong>${prediction.awayTeam}</strong>
                    <div class="small text-muted">Saved at: ${new Date(prediction.timestamp).toLocaleTimeString()}</div>
                </div>
                <button class="btn btn-sm btn-outline-primary toggle-details" data-index="${index}">Details ▼</button>
            </div>
            <div class="prediction-details" id="details-${index}" style="display:none; margin-top:10px;">
                ${Object.entries(prediction.predictions).map(([key, value]) => `
                    <div><strong>${key}:</strong> ${value}</div>
                `).join('')}
            </div>
        `;
        savedPredictionsList.appendChild(div);
    });

    // Add event listeners for each toggle button
    document.querySelectorAll('.toggle-details').forEach(button => {
        button.addEventListener('click', function() {
            const index = this.getAttribute('data-index');
            const detailsDiv = document.getElementById(`details-${index}`);
            if (detailsDiv.style.display === 'none') {
                detailsDiv.style.display = 'block';
                this.innerHTML = 'Hide ▲';
            } else {
                detailsDiv.style.display = 'none';
                this.innerHTML = 'Details ▼';
            }
        });
    });
}


    // Initial display if any saved already
    displaySavedPredictions();
});
