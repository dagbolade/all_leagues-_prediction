document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('predictionForm');

    if (form) {
        form.addEventListener('submit', function() {
            // After prediction result loads, scroll to the result section
            setTimeout(() => {
                const resultsSection = document.getElementById('predictionResultsSection');
                if (resultsSection) {
                    resultsSection.scrollIntoView({ behavior: 'smooth' });
                }
            }, 500); // slight delay to wait for page load
        });
    }
});
